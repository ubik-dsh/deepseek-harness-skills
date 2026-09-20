#!/usr/bin/env python3
"""Publish a text post to a VK community wall, behind a gate the code enforces.

The gate is two-phase and the phase is the point:

    post.py --text "..."                  prints exactly what would be sent, sends nothing
    post.py --text "..." --confirm        sends it

A human has to stand between the two. The script cannot verify that a human agreed - no script
can - but it can refuse to act without a declared confirmation, which is more than the skill this
was built from did: that one carried "never publish without confirmation" in its documentation
and contained no prompt at all.

**There is no undo.** A community token can post and cannot delete: wall.delete, wall.edit and
wall.restore all answer error 27. The only way to remove a post published with this credential is
by hand in the interface. The gate is not a formality here; it is the last moment at which a
mistake is still cheap.

    --target -241624898     the wall, as the community id negated
    --file draft.txt        the text, from a file - better than --text for anything with
                            quotes, newlines or non-breaking spaces in it
    --schedule 1789911152   a unix timestamp, for a post that should wait

Exit codes: 0 sent, 2 no token, 3 a bad target or no content, 4 VK refused, 5 no --confirm.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vk_preflight", HERE / "preflight.py")
vk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vk)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--text", default="", help="the post body")
    parser.add_argument("--file", type=Path, default=None, help="a file with the post body")
    parser.add_argument("--target", required=True,
                        help="the wall, as the community id negated, e.g. -241624898")
    parser.add_argument("--schedule", type=int, default=None,
                        help="a unix timestamp; later than now makes it a scheduled post")
    parser.add_argument("--confirm", action="store_true",
                        help="the human has confirmed THIS text and THIS target")
    parser.add_argument("--env-file", type=Path, default=None)
    args = parser.parse_args()

    token = vk.read_env_file(args.env_file).get("VK_COMMUNITY_TOKEN", "") if args.env_file else ""
    token = token or os.environ.get("VK_COMMUNITY_TOKEN", "")
    if not token:
        print("  no token. Use --env-file, or set VK_COMMUNITY_TOKEN.")
        return 2

    if args.file is not None:
        if not args.file.exists():
            print(f"  no such file: {args.file}")
            return 3
        body = args.file.read_text(encoding="utf-8-sig", errors="replace").rstrip("\n")
    else:
        body = args.text
    if not body.strip():
        print("  nothing to post: pass --text or --file")
        return 3

    owner = args.target.strip()
    if owner.lstrip("-").isdigit() and int(owner) > 0:
        owner = str(-int(owner))
        print(f"  target     {args.target} -> {owner}  (the community id is positive, the "
              f"wall's owner id is negative)")

    # ---- the gate ------------------------------------------------------------------
    effect = "a public post, visible immediately"
    if args.schedule:
        effect = f"scheduled, and it publishes at {args.schedule} unless removed by hand"
    print("")
    print("  WHAT WOULD BE SENT")
    print(f"    target     {owner}")
    print(f"    authority  community token, from_group=1")
    print(f"    effect     {effect}")
    print(f"    length     {len(body)} characters")
    print("    text")
    for line in body.split("\n"):
        print(f"      | {line}")
    print("")
    print("  THERE IS NO UNDO. A community token cannot delete or edit a post;")
    print("  wall.delete answers error 27. Removing this means doing it by hand.")
    print("")

    if not args.confirm:
        print("  NOT SENT. Re-run with --confirm once the human has agreed to THIS text")
        print("  and THIS target. The confirmation covers the content, not the intention.")
        return 5

    # ---- send ----------------------------------------------------------------------
    try:
        made = vk.call("wall.post", token, owner_id=owner, from_group=1, message=body,
                       publish_date=args.schedule)
    except vk.VkError as trouble:
        meaning = vk.MEANING.get(trouble.code)
        print(f"  FAIL       {trouble}")
        if meaning:
            print(f"             {meaning[0]} - {meaning[1]}")
        return 4

    post_id = made.get("post_id") if isinstance(made, dict) else None
    print(f"  SENT       post_id {post_id}")
    print(f"  verify at  https://vk.com/club{owner.lstrip('-')}?w=wall{owner}_{post_id}")
    print("")
    print("  That id is the whole of the API's confirmation. Whether it looks right, and")
    print("  whether it is on the wall at all, is the human's eye - this token cannot read.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
