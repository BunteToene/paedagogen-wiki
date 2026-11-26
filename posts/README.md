# Posts

Jeder Ordner ist ein Post: `post.json` plus Medien (Bilder als JPG, Videos als MP4).

- `approved` wird erst auf `true` gesetzt, wenn im Chat „passt“ kam.
- `publish_at` ist die Zeit in UTC (19:30 Berlin im Winter = 18:30 UTC).
- `type`: `reel`, `carousel` (Feld `images`: Liste aus `{"file": "...jpg", "alt": "..."}`) oder `image`.
- Nach dem Posten steht das Ergebnis unter `status`. Ordner mit `_` am Anfang sind Beispiele.
