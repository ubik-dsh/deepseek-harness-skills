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
    6   --prove-write posted, and the post could NOT be deleted - a human must remove it

Exit 6 is not hypothetical. **A community token can post and cannot delete**: wall.post is
accepted, and wall.delete, wall.edit and wall.restore all answer error 27 "method is
unavailable with group auth". So a write probe on a community token always leaves a post
behind, and the only cleanup is by hand. Run it on a private community, with the human
present, and read the warning.

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
from pathlib import Path

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


def inside_a_repository(path: Path) -> Path | None:
    """The repository this file sits in, if it sits in one.

    A credential inside a working tree is one `git add -A` away from being published. The
    check costs a few `exists()` calls and it is a refusal rather than a warning, because a
    warning here is a warning that gets read after the push.
    """
    for folder in [path.parent, *path.parent.parents]:
        if (folder / ".git").exists():
            return folder
    return None


def read_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines, and only the two names this tool has any use for.

    A quoted value is unwrapped, because a key pasted from a browser occasionally arrives
    with quotes around it and a token with a literal quote on each end fails with an error
    that says nothing about quotes.
    """
    wanted = ("VK_COMMUNITY_TOKEN", "VK_GROUP_ID")
    values: dict[str, str] = {}
    for number, line in enumerate(
            path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
        text = line.strip()
        if text == "" or text.startswith("#"):
            continue
        if "=" not in text:
            raise ValueError(f"line {number} is not KEY=VALUE")
        key, _, value = text.partition("=")
        key = key.strip()
        if key in wanted:
            values[key] = value.strip().strip('"').strip("'")
    return values


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
    parser.add_argument("--env-file", type=Path, default=None,
                        help="read VK_COMMUNITY_TOKEN and VK_GROUP_ID from this file. Only "
                             "the path is passed - the value never reaches a command line, "
                             "a process list or a shell history")
    args = parser.parse_args()

    token = os.environ.get("VK_COMMUNITY_TOKEN", "").strip()
    group_hint = os.environ.get("VK_GROUP_ID", "").strip()

    if args.env_file is not None:
        # The environment variable is the better home for a secret, and it is unusable here:
        # measured on this machine, `setx` writes HKCU\Environment and a process spawned by
        # the already-running harness never sees it, because the harness's own environment
        # block was fixed when it started. So the file exists, and only its path travels.
        if not args.env_file.exists():
            say(f"  no such env file: {args.env_file}")
            return 2
        repository = inside_a_repository(args.env_file)
        if repository is not None:
            say(f"  refusing: {args.env_file} is inside a repository - {repository}")
            say("  A credential in a working tree is one `git add -A` from being published.")
            say("  Move it outside every repository and run again.")
            return 2
        try:
            loaded = read_env_file(args.env_file)
        except (OSError, ValueError) as trouble:
            say(f"  cannot read {args.env_file} - {trouble}")
            return 2
        token = loaded.get("VK_COMMUNITY_TOKEN", "").strip() or token
        group_hint = loaded.get("VK_GROUP_ID", "").strip() or group_hint
        say(f"  env file   {args.env_file}  "
            f"({'no token in it yet' if not token else 'a token is present'})")
    if not token:
        if args.env_file is not None:
            say("")
            say(f"  the file {args.env_file} has no VK_COMMUNITY_TOKEN yet.")
            say("  Open it, put the key after the = on that line, and save.")
            say("  Do not paste the key here, do not pass it as an argument, no quotes.")
            return 2
        say("  no token in the environment.")
        say("")
        say("  Either set VK_COMMUNITY_TOKEN as a USER environment variable, or point at a")
        say("  file with --env-file. Never paste it into a chat, never pass it as an")
        say("  argument. A credential in a transcript is in a log, a backup, and whatever")
        say("  the transcript syncs to.")
        say("")
        say("  The key is made in VK at the community's Управление - Настройки -")
        say("  Работа с API - Создать ключ, with the scopes wall and photos.")
        return 2

    say(f"  token      {fingerprint(token)}")

    # ---- who is this token, and what may it do -------------------------------------
    try:
        who = call("groups.getById", token, group_id=group_hint or None,
                   fields="members_count,description,is_closed,wall,can_post,type")
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

    # The mask arrives with its own decoding: `permissions` is a list of {name, setting}, so
    # the API names what this token may do. The first version printed the raw number "on
    # purpose, because the bits are not decoded from memory" - a reasonable caution that
    # turned out to be unnecessary, since VK decodes them itself and an agent reading the
    # number learns nothing.
    try:
        permissions = call("groups.getTokenPermissions", token)
        named = permissions.get("permissions") if isinstance(permissions, dict) else None
        if named:
            say(f"  permissions {', '.join(str(one.get('name')) for one in named)}")
            say(f"              mask {permissions.get('mask')}")
        else:
            say(f"  permissions {json.dumps(permissions, ensure_ascii=False)}")
    except VkError as trouble:
        say(f"  permissions not available ({trouble})")

    # A community token cannot call wall.get at all - measured, error 27 on every read
    # method. So the wall is only read when a read was actually ASKED for, and its failure
    # only stops the run in that case. The first version read it whenever --target was given
    # and returned 3 on failure, which made --prove-write unreachable in every possible run:
    # the one flag that answers "may this token write" could never be reached, because the
    # step before it always failed for this kind of token.
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
        wanted_read = args.show_wall > 0 or "read" in args.intent
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
            if wanted_read:
                say("             a read was asked for and this token cannot do it. A user "
                    "or service token can; a community token cannot")
                return 3
            say("             expected for a community token, and it does not block a write. "
                "Verification of what was published comes from the returned post_id and "
                "from looking at the community yourself")

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
        say(f"  prove-write  scheduling a post for {future}, then trying to delete it")
        try:
            made = call("wall.post", token, owner_id=f"-{resolved}", from_group=1,
                        message="manage-vk preflight: created to prove write authority, "
                                "scheduled an hour ahead and deleted immediately",
                        publish_date=future)
        except VkError as trouble:
            meaning = MEANING.get(trouble.code)
            say(f"  FAIL         {trouble}")
            if meaning:
                say(f"               {meaning[0]} - {meaning[1]}")
            return 4

        post_id = made.get("post_id") if isinstance(made, dict) else None
        say(f"  proved       wall.post returned post_id={post_id} - this token CAN write")
        if not post_id:
            say("               no post_id came back, so there is nothing to clean up")
            return 0

        try:
            call("wall.delete", token, owner_id=f"-{resolved}", post_id=post_id)
            say("  cleaned      wall.delete succeeded - nothing was left behind")
        except VkError:
            # MEASURED, and it cost a real post: a community token CAN write and CANNOT
            # delete. wall.delete, wall.edit and wall.restore all answer error 27 "method is
            # unavailable with group auth". The first version of this treated a failed
            # cleanup as an ordinary failure, printed one line, and returned - while leaving
            # a scheduled post that publishes an hour later, on a community somebody has to
            # go and clean by hand.
            #
            # A probe that cannot clean up after itself is not self-deleting, and it must say
            # so in a way that cannot be missed, and it must name the action the human owes.
            say("")
            say("  " + "!" * 68)
            say("  A POST WAS LEFT ON THE COMMUNITY, AND THIS TOKEN CANNOT DELETE IT.")
            say(f"  post_id {post_id} on owner -{resolved}, scheduled for {future}.")
            say("  It PUBLISHES at that time unless it is removed by hand.")
            say("")
            say(f"  delete it at  https://vk.com/club{resolved}?w=wall-{resolved}_{post_id}")
            say("  or in the community's wall under its scheduled posts.")
            say("")
            say("  Delete is not available to a community token. Measured: wall.delete,")
            say("  wall.edit and wall.restore all answer error 27 'method is unavailable")
            say("  with group auth'. Only wall.post and wall.closeComments were accepted.")
            say("  " + "!" * 68)
            return 6
    elif args.intent and any(one != "read" for one in args.intent):
        say("")
        say("  Nothing was written. To prove write authority, re-run with --prove-write")
        say("  --confirmed, having confirmed it with the user.")

    say("")
    say("  PREFLIGHT PASSED - the target is where the write will land.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
