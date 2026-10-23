

## Video previews for Messages

App landing pages include static Open Graph video metadata and a player with no autoplay or eager media download. The MP4 is a direct public HTTPS asset; the poster remains available as an image fallback. Legal pages retain their own previews.

`link-previews.json` is the app preview catalog. To update a clip, use a new versioned asset filename, update its dimensions, duration and file sizes in the catalog, then run:

```sh
python3 scripts/link-previews.py --write --probe
```

Use H.264, yuv420p, a fast-start MP4, and a poster at least 900 pixels wide. Keep the video, poster and icons together below 10 MB; this validator reserves 100 KB for icons. Metadata must be in the initial HTML and must not depend on JavaScript. Use only approved footage or sample screenshots without private names, conversations, account details or secrets. Screenshot montages are labeled as screen captures.

Before publication, run `python3 scripts/link-previews.py --probe` and `git diff --check`. After publication, run `python3 scripts/link-previews.py --live` to check exact live HTML, MIME types, sizes and MP4 byte-range support. `--probe` additionally requires FFprobe.

Apple controls autoplay, caching and presentation in Messages. These checks verify the website and media, not delivery or autoplay in a conversation. This metadata applies to these website links; Apple controls the separate App Store and TestFlight link previews.

References: [Apple TN3156](https://developer.apple.com/documentation/technotes/tn3156-create-rich-previews-for-messages) and [Open Graph](https://ogp.me/).
