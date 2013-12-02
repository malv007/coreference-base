# coding=utf-8
__author__ = 'Josu Bermudez <josu.bermudez@deusto.es>'


stop_words=set(("aber", "alle", "allem", "allen", "aller", "alles", "als", "also", "am", "an", "ander", "andere", "anderem",
                "anderen", "anderer", "anderes", "anderm", "andern", "anderr", "anders", "auch", "auf", "aus", "bei", "bin",
                "bis", "bist", "da", "damit", "dann", "der", "den", "des", "dem", "die", "das", "daß", "derselbe", "derselben",
                "denselben", "desselben", "demselben", "dieselbe", "dieselben", "dasselbe", "dazu", "dein", "deine", "deinem",
                "deinen", "deiner", "deines", "denn", "derer", "dessen", "dich", "dir", "du", "dies", "diese", "diesem", "diesen",
                "dieser", "dieses", "doch", "dort", "durch", "ein", "eine", "einem", "einen", "einer", "eines", "einig", "einige",
                "einigem", "einigen", "einiger", "einiges", "einmal", "er", "ihn", "ihm", "es", "etwas", "euer", "eure", "eurem",
                "euren", "eurer", "eures", "für", "gegen", "gewesen", "hab", "habe", "haben", "hat", "hatte", "hatten", "hier",
                "hin", "hinter", "ich", "mich", "mir", "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres", "euch", "im", "in",
                "indem", "ins", "ist", "jede", "jedem", "jeden", "jeder", "jedes", "jene", "jenem", "jenen", "jener", "jenes", "jetzt",
                "kann", "kein", "keine", "keinem", "keinen", "keiner", "keines", "können", "könnte", "machen", "man", "manche", "manchem",
                "manchen", "mancher", "manches", "mein", "meine", "meinem", "meinen", "meiner", "meines", "mit", "muss", "musste", "nach",
                "nicht", "nichts", "noch", "nun", "nur", "ob", "oder", "ohne", "sehr", "sein", "seine", "seinem", "seinen", "seiner", "seines",
                "selbst", "sich", "sie", "ihnen", "sind", "so", "solche", "solchem", "solchen", "solcher", "solches", "soll", "sollte",
                "sondern", "sonst", "über", "um", "und", "uns", "unse", "unsem", "unsen", "unser", "unses", "unter", "viel", "vom", "von",
                "vor", "während", "war", "waren", "warst", "was", "weg", "weil", "weiter", "welche", "welchem", "welchen",
                "welcher", "welches", "wenn", "werde", "werden", "wie", "wieder", "will", "wir", "wird", "wirst", "wo", "wollen", "wollte",
                "würde", "würden", "zu", "zum", "zur", "zwar", "zwischen"))


non_words = ("mm","hmm","ahem","um")
invalid_stop_words = ("u.s.", "u.k", "u.s.s.r.", "there", "ltd.")
invalid_start_words = ("'s",  "etc", )
invalid_end_words = ("etc", )

location_modifiers = ("east", "west", "north", "south",
                              "eastern", "western", "northern", "southern", "upper", "lower")