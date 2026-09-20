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
import json
import os
import sys
import urllib.request
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vk_preflight", HERE / "preflight.py")
vk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vk)


def upload_photo(token: str, path: Path) -> str | None:
    """Upload one image by the only route a community token has, and return `photo<owner>_<id>`.

    The wall upload server is refused (error 27). The messages upload server is not, so:
    get a server, POST the file as multipart, save with `photos.saveMessagesPhoto`.

    **The body is built by hand and the boundary is written into the header**, and that is
    deliberate rather than primitive. A fresh agent reported that urllib and `requests` both got
    `{"photo": ""}` from this host while `curl -F` worked, and concluded that Python's multipart
    is refused. **That did not reproduce**: on the same day, on this host, a hand-built body,
    `requests`, and `curl -F` each returned a filled `photo` field for the same two files.
    Whatever that agent met, it was not "Python's multipart".

    So this uses the standard library with the body written out, and the diagnostic is recorded
    instead of a rule: **an empty `photo` with HTTP 200 means the host received a POST whose file
    field did not arrive.** If this function ever returns that, the body is the thing to suspect,
    `curl -F photo=@<file>` is the control that separates the two, and **a `upload_url` is
    single-use** - posting to one twice, which is what a loop over three clients does, fails on
    the second attempt and looks exactly like a broken client.
    """
    server = vk.call("photos.getMessagesUploadServer", token,
                     group_id=os.environ.get("VK_GROUP_ID") or None)
    url = server.get("upload_url")
    if not url:
        print(f"  FAIL       no upload_url in {str(server)[:120]}")
        return None

    boundary = "----dsh" + uuid.uuid4().hex
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="{path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n").encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(
        url, data=head + path.read_bytes() + tail,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(request, timeout=120) as answer:
            sent = json.loads(answer.read().decode("utf-8", errors="replace"))
    except Exception as trouble:                                # noqa: BLE001
        print(f"  FAIL       the upload host: {type(trouble).__name__}: {trouble}")
        return None

    if not sent.get("photo"):
        print("  FAIL       the upload host accepted the POST and returned an empty photo")
        print(f"             field - {json.dumps(sent)[:160]}")
        print("             the body is what to suspect; `curl -F photo=@<file>` is the control")
        return None

    saved = vk.call("photos.saveMessagesPhoto", token,
                    server=sent["server"], photo=sent["photo"], hash=sent["hash"])
    photo = saved[0] if isinstance(saved, list) and saved else saved
    return f"photo{photo.get('owner_id')}_{photo.get('id')}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--text", default="", help="the post body")
    parser.add_argument("--file", type=Path, default=None, help="a file with the post body")
    parser.add_argument("--target", required=True,
                        help="the wall, as the community id negated, e.g. -241624898")
    parser.add_argument("--schedule", type=int, default=None,
                        help="a unix timestamp; later than now makes it a scheduled post")
    parser.add_argument("--photo", type=Path, default=None,
                        help="an image to upload and try to attach. The upload works and VK is "
                             "expected to DROP the attachment - check the wall, then add it by "
                             "editing the post in the interface")
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

    # ---- the picture, if there is one ----------------------------------------------
    # The upload works and the ATTACH is what fails: wall.post takes `attachments`, returns a
    # post_id, and VK drops a photo from the messages album without a word. Measured on
    # 2026-09-20 on community 241624898, and re-confirmed by a fresh agent the same day by
    # reloading the wall and looking. It is stated with the date because it is an observation
    # about one host, not a law - and a reader cannot tell those apart unless the difference is
    # written down.
    attachment = None
    if args.photo:
        uploaded = upload_photo(token, args.photo)
        if uploaded is None:
            return 4
        attachment = uploaded
        print("")
        print(f"  picture    uploaded and saved as {attachment}")
        print("             VK IS EXPECTED TO DROP THIS ATTACHMENT. Every measurement so far")
        print("             says a photo from the messages album does not reach a wall post,")
        print("             and wall.post will not say so - it returns a post_id either way.")
        print("             Check the wall. If it is not there, add it by editing the post in")
        print("             the interface - see references/editing-a-post-in-the-interface.md.")

    # ---- send ----------------------------------------------------------------------
    try:
        made = vk.call("wall.post", token, owner_id=owner, from_group=1, message=body,
                       publish_date=args.schedule, attachments=attachment)
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
    if attachment:
        print("")
        print("  AND WITH A PICTURE, LOOK AT THE WALL BEFORE BELIEVING ANYTHING. The reply is")
        print("  identical whether the attachment landed or was dropped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
