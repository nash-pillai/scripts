#!/usr/bin/env bash
# Rofi script mode for clipboard history with timestamps and image previews.

TIMESTAMP_FILE="${HOME}/.local/share/cliphist-meta/timestamps"
CACHE_DIR="/tmp/cliphist"

# Handle selection — ROFI_INFO has the original cliphist line
if [[ -n "$ROFI_INFO" ]]; then
    cliphist decode <<<"$ROFI_INFO" | wl-copy
    exit 0
fi

mkdir -p "$CACHE_DIR"

cliphist list | gawk -v cache="$CACHE_DIR" -v tsfile="$TIMESTAMP_FILE" -v now="$(date +%s)" '
BEGIN {
    FS = "\t"
    while ((getline line < tsfile) > 0) {
        split(line, parts, "\t")
        ts[parts[1]] = parts[2]
    }
    close(tsfile)
}
/^[0-9]+\t<meta http-equiv=/ { next }
{
    id = $1
    line = $0
    content = $0
    sub(/^[0-9]+\t/, "", content)

    # Relative time
    ago = ""
    if (id in ts && ts[id] > 0) {
        diff = now - ts[id]
        if (diff < 60) ago = diff "s"
        else if (diff < 3600) ago = int(diff/60) "m"
        else if (diff < 86400) ago = int(diff/3600) "h"
        else ago = int(diff/86400) "d"
    }

    # Compact display for list row
    short = content
    if (length(short) > 80) short = substr(short, 1, 80) "..."

    if (match(content, /binary.* (jpg|jpeg|png|bmp|webp)/, grp)) {
        ext = grp[1]
        imgpath = cache "/" id "." ext
        system("test -f " imgpath " || echo " id "\\\\t | cliphist decode > " imgpath)

        if (ago != "")
            printf "%s\0info\x1f%s\x1ficon\x1f%s\x1fdisplay\x1f%s  %s\n", \
                content, line, imgpath, ago, short
        else
            printf "%s\0info\x1f%s\x1ficon\x1f%s\x1fdisplay\x1f%s\n", \
                content, line, imgpath, short
    } else {
        if (ago != "")
            printf "%s\0info\x1f%s\x1fdisplay\x1f%s  %s\n", \
                content, line, ago, short
        else
            printf "%s\0info\x1f%s\x1fdisplay\x1f%s\n", \
                content, line, short
    }
}
'
