#!/usr/bin/env python3
"""Prove the VK target and the token's authority before anything is published.

Read-only by construction. It posts nothing, writes nothing, opens no browser, and has no
flag that makes it do any of those - the skill this was built from shipped a `--check` that
reached `subprocess.Popen` and could launch a browser on an open debugging port, which is
how a dry run becomes an action.

The one exception is `--prove-write`, and it is the exception that proves the rule. A
permission mask cannot tell you whether a token may write; only a write can. So with that
flag the script creates a post scheduled far in the future - never visible, admins only -
reads its id back, and deletes it. The round trip is the evidence, and it leaves nothing.

    python preflight.py                                  who is this token
    python preflight.py --target -241624898 --show-wall 5
    python preflight.py --intent post --intent photo
    python preflight.py --prove-write --confirmed        the only write, undone

Exit codes:

    0   the token works and the target resolves
    2   no token in the environment
    3   the token works but not for what was asked of it
    4   VK answered with an error object
    5   --prove-write was asked for without --confirmed

The token comes from VK_COMMUNITY_TOKEN and from nowhere else. It is never printed, never
taken from an argument, and never read from a file this script created.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.vk.com/method/"
VERSION = "5.199"

# VK's ceiling is a few requests per second and it differs by method. Spacing every call is
# cheaper than discovering the ceiling, and a block looks exactly like a broken token.
GAP_SECONDS = 0.4
_last_call = [0.0]


def say(message: str = "") -> None:
    print(message)


def spaced() -> None:
    waited = time.monotonic() - _last_call[0]
    if waited < GAP_SECONDS:
        time.sleep(GAP_SECONDS - waited)
    _last_call[0] = time.monotonic()


class VkError(Exception):
    """A failure VK reported in the body of an HTTP 200."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"VK error {code}: {message}")
        self.code = code
        self.message = message


def call(method: str, token: str, **params: object) -> object:
    """One API call, with the body checked - not the status code.

    Measured without a token:

        GET groups.getById?group_id=241624898&v=5.199
        -> HTTP 200
           {"error":{"error_code":15,"error_msg":"Access denied: token required"}}

    A client that reads `status_code` treats a refused call as a delivered post. That is the
    single most expensive mistake available in this API.
    """
    query = {key: str(value) for key, value in params.items() if value is not None}
    query["access_token"] = token
    query["v"] = VERSION

    spaced()
    request = urllib.request.Request(
        API + method + "?" + urllib.parse.urlencode(query),
        headers={"User-Agent": "dsh-manage-vk/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=25) as answer:
            body = json.loads(answer.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as trouble:
        raise VkError(trouble.code, f"HTTP {trouble.code} from the API host") from trouble
    except (urllib.error.URLError, TimeoutError) as trouble:
        raise VkError(0, f"the API was not reachable - {trouble}") from trouble
    except json.JSONDecodeError as trouble:
        raise VkError(0, f"the reply was not JSON - {trouble}") from trouble

    if isinstance(body, dict) and "error" in body:
        one = body["error"]
        raise VkError(int(one.get("error_code", 0)), str(one.get("error_msg", "")))
    if isinstance(body, dict) and "response" in body:
        return body["response"]
    raise VkError(0, f"a reply with neither response nor error - {str(body)[:120]}")


# What an error means and what to do about it. Only the codes whose meaning is either
# measured here or stated in VK's own public method documentation are listed; the rest are
# reported with their number and no invented explanation.
MEANING = {
    5: ("the token was refused", "check that the key is the COMMUNITY key and that "
                                 "Long Poll or the API section is enabled for the group"),
    6: ("too many requests per second", "retryable - wait longer and send fewer"),
    9: ("too many requests per day", "not retryable today"),
    14: ("the captcha was required", "interactive; a community token normally avoids this"),
    15: ("access denied, token required", "the token is absent or empty"),
    27: ("the group key is not valid for this action", "usually a missing scope, or the "
                                                      "group key was revoked"),
    100: ("one of the parameters is wrong", "read the message - it names the parameter"),
    214: ("the wall is not writable by this token", "the wall is disabled or not permitted"),
}


def fingerprint(token: str) -> str:
    """Enough to tell two tokens apart, not enough to use one."""
    return f"{len(token)} chars, starting {token[:4]}..."


def main() -> int:
    # A cp1251 console cannot encode a mixed-script message, and a crash while reporting a
    # finding is the finding thrown away. The scanner in find-a-skill learned this first.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", help="the community to inspect, as a numeric id "
                                         "(positive or negative) or a screen name")
    parser.add_argument("--show-wall", type=int, default=0,
                        help="how many recent wall posts to read")
    parser.add_argument("--intent", action="append", default=[],
                        choices=["post", "photo", "schedule", "read"],
                        help="what is about to be asked of this token; repeatable")
    parser.add_argument("--prove-write", action="store_true",
                        help="the one write - a future-dated post, read back and deleted")
    parser.add_argument("--confirmed", action="store_true",
                        help="the user has explicitly confirmed the --prove-write action")
    args = parser.parse_args()

    token = os.environ.get("VK_COMMUNITY_TOKEN", "").strip()
    if not token:
        say("  no token in the environment.")
        say("")
        say("  Set VK_COMMUNITY_TOKEN as a USER environment variable - never paste it into")
        say("  a chat, never pass it as an argument, never write it into a file this tool")
        say("  created. A credential in a transcript is in a log, a backup, and whatever")
        say("  the transcript syncs to.")
        say("")
        say("  The key is made in VK at the community's Управление - Настройки -")
        say("  Работа с API - Создать ключ, with the scopes wall and photos.")
        return 2

    say(f"  token      {fingerprint(token)}")

    # ---- who is this token, and what may it do -------------------------------------
    try:
        who = call("groups.getById", token,
                   group_id=os.environ.get("VK_GROUP_ID") or None)
    except VkError as trouble:
        code = trouble.code
        meaning = MEANING.get(code)
        say(f"  FAIL       {trouble}")
        if meaning:
            say(f"             {meaning[0]} - {meaning[1]}")
        return 4

    groups = who.get("groups", who) if isinstance(who, dict) else who
    if isinstance(groups, list) and groups:
        first = groups[0]
        say(f"  community  {first.get('name')!r}  id={first.get('id')}  "
            f"screen={first.get('screen_name')}")
        say(f"  type       {first.get('type')}  members={first.get('members_count')}")
        resolved = first.get("id")
    else:
        say(f"  community  VK returned {str(who)[:140]}")
        resolved = None

    # The permission mask is printed raw. Its bits are not decoded here, because decoding
    # them from memory is exactly the kind of received claim this family keeps catching.
    try:
        permissions = call("groups.getTokenPermissions", token)
        say(f"  mask       {json.dumps(permissions, ensure_ascii=False)}")
        say("             printed raw on purpose - the bits are not decoded from memory")
    except VkError as trouble:
        say(f"  mask       not available ({trouble})")

    # ---- the target ---------------------------------------------------------------
    if args.target:
        raw = args.target.strip()
        owner_id = raw
        if raw.lstrip("-").isdigit():
            number = int(raw)
            if number > 0:
                # The sign is the most common single mistake in this API, and it fails in a
                # way that looks like a permissions problem. Say it out loud instead.
                owner_id = str(-number)
                say(f"  target     {raw} -> {owner_id}  (the community id is positive, "
                    f"the wall's owner id is negative)")
            else:
                say(f"  target     {owner_id}  (already negative)")
        try:
            wall = call("wall.get", token, owner_id=owner_id,
                        count=max(args.show_wall, 1))
            posts = wall.get("items", []) if isinstance(wall, dict) else []
            say(f"  wall       readable, {wall.get('count', '?')} post(s) in total")
            for one in posts[:args.show_wall]:
                text = " ".join(str(one.get("text", "")).split())[:78]
                say(f"             [{one.get('id')}] {one.get('date')} {text!r}")
        except VkError as trouble:
            say(f"  wall       NOT readable - {trouble}")
            say("             a wall that cannot be read is not a wall that can be written")
            return 3

    # ---- is the token good for what is about to be asked --------------------------
    if args.intent:
        say(f"  intent     {', '.join(args.intent)}")
        say("             read access is proven above. **Write access is not, and cannot "
            "be**, from a mask or a successful read - only a write proves a write.")
        if "photo" in args.intent:
            try:
                upload = call("photos.getWallUploadServer", token,
                              group_id=resolved if resolved else None)
                say(f"  photo      an upload server was issued: "
                    f"{'yes' if upload else 'no'} - the photos scope is present")
            except VkError as trouble:
                say(f"  photo      NOT available - {trouble}")
                return 3

    # ---- the one write, and it undoes itself --------------------------------------
    if args.prove_write:
        if not args.confirmed:
            say("")
            say("  --prove-write needs --confirmed, and the confirmation must come from the")
            say("  user about THIS action. The script cannot verify that a human agreed; it")
            say("  can refuse to act without a declared one, which is the most a script can")
            say("  do and is more than the skill this came from did.")
            return 5
        if not resolved:
            say("  --prove-write needs a resolvable community; --target or VK_GROUP_ID")
            return 3
        future = int(time.time()) + 3600
        say("")
        say(f"  prove-write  scheduling a post for {future} and deleting it immediately")
        try:
            made = call("wall.post", token, owner_id=f"-{resolved}", from_group=1,
                        message="manage-vk preflight: this post is created and deleted "
                                "within the same second and is never visible",
                        publish_date=future)
            post_id = made.get("post_id") if isinstance(made, dict) else None
            say(f"  proved       wall.post returned post_id={post_id}")
            if post_id:
                call("wall.delete", token, owner_id=f"-{resolved}", post_id=post_id)
                say("  cleaned      wall.delete called - nothing was left behind")
        except VkError as trouble:
            code = trouble.code
            meaning = MEANING.get(code)
            say(f"  FAIL         {trouble}")
            if meaning:
                say(f"               {meaning[0]} - {meaning[1]}")
            return 4
    elif args.intent and any(one != "read" for one in args.intent):
        say("")
        say("  Nothing was written. To prove write authority, re-run with --prove-write")
        say("  --confirmed, having confirmed it with the user.")

    say("")
    say("  PREFLIGHT PASSED - the target is where the write will land.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
