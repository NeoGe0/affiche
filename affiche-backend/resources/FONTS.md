# Bundled fonts

The `.ttf` files in this directory are **third-party fonts redistributed with Affiche**. They are
**not** covered by Affiche's AGPL-3.0 license — each family keeps its own license, and every one of
them is under the [SIL Open Font License 1.1](https://openfontlicense.org/).

The OFL allows bundling and redistribution (including inside a Docker image), on the condition that
the license and its copyright notice travel with the font files. That is what `licenses/` is for:
each family's `OFL.txt` is copied verbatim from its upstream source.

Fonts the user uploads at runtime land in `<CONFIG_DIR>/fonts/` instead, and are the user's own
responsibility.

| Family | Copyright | License |
|---|---|---|
| Anton | Copyright 2020 The Anton Project Authors | [OFL 1.1](licenses/Anton-OFL.txt) |
| Bebas Neue | Copyright © 2010 by Dharma Type | [OFL 1.1](licenses/BebasNeue-OFL.txt) |
| Buda | Copyright (c) 2010, Adèle Antignac — RFN "Buda" | [OFL 1.1](licenses/Buda-OFL.txt) |
| Bungee Shade | Copyright 2023 The Bungee Project Authors | [OFL 1.1](licenses/BungeeShade-OFL.txt) |
| Cinzel | Copyright 2020 The Cinzel Project Authors | [OFL 1.1](licenses/Cinzel-OFL.txt) |
| Edu SA Hand | Copyright 2022 The AU School Handwriting Fonts Project Authors | [OFL 1.1](licenses/EduSAHand-OFL.txt) |
| League Spartan | Copyright 2020 The League Spartan Project Authors | [OFL 1.1](licenses/LeagueSpartan-OFL.txt) |
| Macondo | Copyright © 1997–2011, John Vargas Beltrán — RFN "Macondo" | [OFL 1.1](licenses/Macondo-OFL.txt) |
| Monoton | Copyright (c) 2011 by vernon adams — RFN "Monoton" | [OFL 1.1](licenses/Monoton-OFL.txt) |
| Oswald | Copyright 2016 The Oswald Project Authors | [OFL 1.1](licenses/Oswald-OFL.txt) |
| Playfair Display | Copyright 2017 The Playfair Display Project Authors — RFN "Playfair Display" | [OFL 1.1](licenses/PlayfairDisplay-OFL.txt) |
| Quintessential | Copyright (c) 2012, Brian J. Bonislawsky DBA Astigmatic — RFN "Quintessential" | [OFL 1.1](licenses/Quintessential-OFL.txt) |
| Sixtyfour | Copyright 2021 The Sixtyfour Project Authors | [OFL 1.1](licenses/Sixtyfour-OFL.txt) |
| Uncial Antiqua | Copyright (c) 2011 by Brian J. Bonislawsky DBA Astigmatic — RFN "Uncial Antiqua" | [OFL 1.1](licenses/UncialAntiqua-OFL.txt) |

*RFN = Reserved Font Name: a modified version of that font may not be distributed under the
reserved name.*

All families were obtained from [Google Fonts](https://fonts.google.com/)
([google/fonts](https://github.com/google/fonts), `ofl/`), which is also where the license files
here come from.

## Adding a font to the bundle

1. Check the license actually permits redistribution (OFL and Apache 2.0 do; "free for personal
   use" does **not**).
2. Drop the `.ttf`/`.otf` next to the others — `TextRenderer.list_available_fonts()` globs this
   directory by extension, so nothing else to register.
3. Copy the upstream license verbatim to `licenses/<Family>-OFL.txt` and add a row above.
