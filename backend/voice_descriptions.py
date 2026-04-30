"""Curated descriptions + trait tags for the voices shipped by each engine.

Applied once at startup by `_seed_voice_profiles()` in `main.py`: any
`(engine, voice_id)` without a profile row yet is inserted with the values
here. User edits in the wizard override these and are never clobbered.

Each entry:
    description — 1–2 sentences on timbre / best fit
    traits      — short list of tone tags (for Step 2 facet filters)
"""

from __future__ import annotations


# Canonical trait vocabulary. Step 2 filters derive their facet list from
# whatever traits actually appear in seeded + user-edited voices.
TRAIT_VOCAB = [
    "warm", "cold",
    "bright", "dark",
    "soft", "crisp",
    "youthful", "mature",
    "calm", "energetic",
    "gentle", "assertive", "commanding", "gravitas",
    "playful", "serious",
    "breathy", "nasal", "deep", "high",
    "theatrical", "grounded",
    "intimate", "narrator",
    "menacing", "cheerful", "melancholy",
    "posh", "casual",
]


VOICE_INFO: dict[tuple[str, str], dict] = {

    # ─────────────────────────────────────────────────────────────
    # Kokoro — 21 voices (American male/female, British male/female)
    # ─────────────────────────────────────────────────────────────

    ("kokoro", "af_heart"): {
        "description": "Warm, grounded American-female voice with soft emotive colouring. "
                       "Kokoro's flagship female — sincere, versatile, comfortable in dialogue.",
        "traits": ["warm", "gentle", "grounded"],
    },
    ("kokoro", "af_bella"): {
        "description": "Bright, youthful American female. Energetic, slightly bubbly cadence — "
                       "suits upbeat characters or cheerful narration.",
        "traits": ["bright", "youthful", "energetic"],
    },
    ("kokoro", "af_nicole"): {
        "description": "Calm, measured American female with a newsreader-neutral edge. "
                       "Professional, clean, unemotional — good for exposition.",
        "traits": ["calm", "crisp", "narrator"],
    },
    ("kokoro", "af_kore"): {
        "description": "Lower-register American female; grave and steady. "
                       "Reads serious or resolved lines without becoming cold.",
        "traits": ["dark", "serious", "mature"],
    },
    ("kokoro", "af_sarah"): {
        "description": "Neutral, clear American female — a flexible workhorse voice. "
                       "Good default when the line shouldn't push a personality.",
        "traits": ["crisp", "grounded"],
    },
    ("kokoro", "af_sky"): {
        "description": "Light, slightly breathy American female. Youthful and soft — "
                       "can feel naive, tender, or uncertain.",
        "traits": ["soft", "youthful", "breathy", "gentle"],
    },
    ("kokoro", "af_nova"): {
        "description": "Cool, poised American female. Slightly detached delivery — "
                       "suits sharp or analytical characters.",
        "traits": ["cold", "crisp", "assertive"],
    },
    ("kokoro", "af_aoede"): {
        "description": "Lyrical, slightly theatrical American female. Melodic cadence — "
                       "good for expressive, literary, or monologue text.",
        "traits": ["theatrical", "bright", "narrator"],
    },

    ("kokoro", "am_michael"): {
        "description": "Mid-range, affable American male. Conversational 'nice guy' timbre — "
                       "reliable for dialogue and friendly narration.",
        "traits": ["warm", "grounded", "casual"],
    },
    ("kokoro", "am_fenrir"): {
        "description": "Deeper American male with a slight edge. Projects quiet strength — "
                       "suits confident or gruff characters.",
        "traits": ["deep", "assertive", "mature"],
    },
    ("kokoro", "am_onyx"): {
        "description": "Lowest-register American male. Rich, grave — "
                       "can tip into ominous or heavy gravitas.",
        "traits": ["deep", "dark", "gravitas", "menacing"],
    },
    ("kokoro", "am_puck"): {
        "description": "Lighter, playful American male. Mischievous timbre — "
                       "suits trickster, teen, or unserious roles.",
        "traits": ["bright", "youthful", "playful"],
    },
    ("kokoro", "am_adam"): {
        "description": "Baritone American male. Authoritative and steady — "
                       "classic lead / narrator delivery.",
        "traits": ["deep", "commanding", "narrator"],
    },

    ("kokoro", "bf_emma"): {
        "description": "Soft British female (RP-leaning). Gentle, polite, "
                       "slightly reserved — understated emotional reads.",
        "traits": ["soft", "posh", "gentle"],
    },
    ("kokoro", "bf_isabella"): {
        "description": "Warm British female with expressive colouring. "
                       "Poised but emotionally available — good for charged scenes.",
        "traits": ["warm", "posh", "theatrical"],
    },
    ("kokoro", "bf_alice"): {
        "description": "Crisp RP British female. Brighter and more neutral — "
                       "reads as composed, confident, politely friendly.",
        "traits": ["crisp", "posh", "bright"],
    },
    ("kokoro", "bf_lily"): {
        "description": "Youthful British female — light and cheerful, "
                       "slightly girlish. Suits perky or innocent characters.",
        "traits": ["bright", "youthful", "cheerful"],
    },
    ("kokoro", "bm_george"): {
        "description": "Mid-depth British male, measured and cultured. "
                       "Classic narrator or upper-class-character delivery.",
        "traits": ["mature", "posh", "narrator"],
    },
    ("kokoro", "bm_daniel"): {
        "description": "Warmer British male; approachable baritone. "
                       "Conversational reads with a gentle gravitas.",
        "traits": ["warm", "deep", "grounded"],
    },
    ("kokoro", "bm_fable"): {
        "description": "Storyteller British male. Slightly rich, theatrical — "
                       "pitched for narrated fantasy, whimsy, bedtime-story reads.",
        "traits": ["theatrical", "narrator", "warm"],
    },

    # ─────────────────────────────────────────────────────────────
    # Orpheus — 8 voices (canonical Orpheus-TTS set)
    # ─────────────────────────────────────────────────────────────

    ("orpheus", "tara"): {
        "description": "Airy, expressive young-adult female. Orpheus's default demo voice — "
                       "natural cadence with subtle breathiness.",
        "traits": ["bright", "youthful", "breathy"],
    },
    ("orpheus", "leah"): {
        "description": "Bright, cheerful female. Youthful and energetic — "
                       "pushes upbeat delivery easily.",
        "traits": ["bright", "youthful", "energetic", "cheerful"],
    },
    ("orpheus", "jess"): {
        "description": "Grounded, warm female voice. Slightly lower than leah, "
                       "more measured — good for reflective or composed lines.",
        "traits": ["warm", "grounded", "mature"],
    },
    ("orpheus", "mia"): {
        "description": "Gentle, soft female. Intimate conversational tone — "
                       "close-mic feel; suits tender or vulnerable passages.",
        "traits": ["soft", "intimate", "gentle"],
    },
    ("orpheus", "zoe"): {
        "description": "Crisp, confident female. Sharper articulation — "
                       "suits assertive, decisive characters.",
        "traits": ["crisp", "assertive", "bright"],
    },
    ("orpheus", "leo"): {
        "description": "Deep, gravelly male with dominant presence. "
                       "Authoritative and weighty — good for commanding or threatening lines.",
        "traits": ["deep", "commanding", "gravitas", "menacing"],
    },
    ("orpheus", "dan"): {
        "description": "Neutral, approachable American-male. Everyman quality — "
                       "comfortable workhorse for lead narration.",
        "traits": ["grounded", "narrator", "casual"],
    },
    ("orpheus", "zac"): {
        "description": "Cool, slightly detached male. Younger feel than leo or dan — "
                       "reads as composed, a little distant.",
        "traits": ["cold", "youthful", "crisp"],
    },

    # ─────────────────────────────────────────────────────────────
    # Hume Octave — named personas + archetype roles.
    # Descriptions here cover the most reusable voices; the rest are
    # auto-described from their label via _label_to_description().
    # ─────────────────────────────────────────────────────────────

    ("hume", "176a55b1-4468-4736-8878-db82729667c1"): {
        "description": "Nature-documentary narrator. Hushed, reverent, paced — "
                       "good for observational narration or atmospheric passages.",
        "traits": ["calm", "narrator", "soft"],
    },
    ("hume", "88e0c3f6-6f99-4e37-a3f4-a053869d6bd4"): {
        "description": "Old-school radio announcer. Booming, theatrical, mid-century — "
                       "suits stylised narration or cinematic flourishes.",
        "traits": ["theatrical", "commanding", "narrator"],
    },
    ("hume", "c11052f5-96df-4c0e-9bba-07e0ad19c4b3"): {
        "description": "Dramatic movie-trailer narrator. Low, pulsing, controlled intensity — "
                       "deploys gravitas without shouting.",
        "traits": ["deep", "gravitas", "commanding"],
    },
    ("hume", "445d65ed-a87f-4140-9820-daf6d4f0a200"): {
        "description": "Booming American narrator. Full chest resonance — "
                       "documentary / feature-film voice-over feel.",
        "traits": ["deep", "narrator", "commanding"],
    },
    ("hume", "84aaf67b-dcab-409d-9f48-8c4aa7abbb24"): {
        "description": "Booming British narrator. Grand, sonorous — "
                       "prestige-doc / period-drama narration.",
        "traits": ["deep", "posh", "narrator"],
    },
    ("hume", "4652d91b-edaf-42c5-abd4-904009422de3"): {
        "description": "Articulate ASMR British narrator. Soft, close, deliberate — "
                       "intimate reads; emphasises breath and sibilance.",
        "traits": ["soft", "intimate", "breathy", "posh"],
    },
    ("hume", "aeaaf1f8-fe31-49ae-893d-c744e5207bc2"): {
        "description": "Relaxing ASMR woman. Whispery, unhurried — "
                       "sleep-adjacent calm; good for tender private moments.",
        "traits": ["soft", "breathy", "intimate", "calm"],
    },
    ("hume", "f898a92e-685f-43fa-985b-a46920f0650b"): {
        "description": "Mysterious woman. Low, breathy, deliberate — "
                       "reads as alluring or dangerously poised.",
        "traits": ["dark", "breathy", "intimate"],
    },
    ("hume", "b201d214-914c-4d0a-b8e4-54adfc14a0dd"): {
        "description": "Inspiring woman. Clear, uplifted, warm — "
                       "TED-talk cadence without feeling canned.",
        "traits": ["warm", "bright", "narrator"],
    },
    ("hume", "8c7d03bd-20d4-40e9-aca1-0469af8ae450"): {
        "description": "Inspiring man. Composed, earnest, forward-leaning — "
                       "CEO-keynote energy with genuine warmth.",
        "traits": ["warm", "grounded", "commanding"],
    },
    ("hume", "de314c2f-0013-4e7c-92d0-f60ca114ff5b"): {
        "description": "Inspiring older guy. Seasoned timbre, measured warmth — "
                       "mentor/father-figure delivery.",
        "traits": ["warm", "mature", "gravitas"],
    },
    ("hume", "9c5a3d53-4a8c-4fa2-adad-8e61a830d0e8"): {
        "description": "Deep male conversational voice. Calm, low, intimate — "
                       "podcast-host baseline; doesn't force affect.",
        "traits": ["deep", "calm", "casual"],
    },
    ("hume", "99d2cb9c-9011-4ead-8734-641656d3df66"): {
        "description": "Comforting male conversationalist. Gentle, unhurried — "
                       "reads as the friend who talks you down.",
        "traits": ["soft", "warm", "gentle"],
    },
    ("hume", "b152864b-6720-496a-9d18-eaadb31516ee"): {
        "description": "Soft male conversationalist. Hushed, attentive — "
                       "good for low-stakes private dialogue.",
        "traits": ["soft", "intimate", "calm"],
    },
    ("hume", "d1248151-8613-41c1-b524-4ce242b02090"): {
        "description": "Conversational English guy. Neutral, friendly — "
                       "everyman conversational range.",
        "traits": ["grounded", "casual", "posh"],
    },
    ("hume", "5add9038-28df-40a6-900c-2f736d008ab3"): {
        "description": "English casual conversationalist. Understated, warm — "
                       "no theatrical edge, just relaxed delivery.",
        "traits": ["warm", "casual", "posh"],
    },
    ("hume", "d6fd5cc2-53e6-4e80-ba83-93972682386a"): {
        "description": "Demure conversationalist. Quiet, reserved, polite — "
                       "under-confident or gentle characters.",
        "traits": ["soft", "gentle"],
    },
    ("hume", "71de875d-bc14-4ed5-87da-8584ba4ea247"): {
        "description": "Serene assistant. Even, precise, unruffled — "
                       "classic AI-assistant tonality without being robotic.",
        "traits": ["calm", "crisp"],
    },
    ("hume", "33045fd9-8010-43f6-b6b0-da3fbf326c29"): {
        "description": "Casual podcast host. Mid-tempo, lightly improvised feel — "
                       "reads like he's thinking as he speaks.",
        "traits": ["casual", "grounded"],
    },
    ("hume", "f3f69312-095c-4ec3-8e50-6961c676e898"): {
        "description": "Cool journalist. Polished, measured, slightly sceptical — "
                       "prestige-podcast lean.",
        "traits": ["crisp", "mature", "narrator"],
    },
    ("hume", "01854384-4e4e-48d4-90d1-b22f760a58b5"): {
        "description": "Male podcaster. Warm-friendly, confident mic presence — "
                       "conversational host energy.",
        "traits": ["warm", "grounded", "casual"],
    },
    ("hume", "96ee3964-5f3f-4a5a-be09-393e833aaf0e"): {
        "description": "Imani Carter. Poised American-female lead — "
                       "measured, assured, faintly sardonic edge.",
        "traits": ["crisp", "assertive", "mature"],
    },
    ("hume", "c7aa10be-57c1-4647-9306-7ac48dde3536"): {
        "description": "Lady Elizabeth. Cultured British-female — "
                       "composed, aristocratic, lightly amused.",
        "traits": ["posh", "mature", "gravitas"],
    },
    ("hume", "06646694-ba2a-4bca-ae3c-71d79c6b04a3"): {
        "description": "Geraldine Wallace. Warm older American female — "
                       "grandmotherly poise, gentle authority.",
        "traits": ["warm", "mature", "gentle"],
    },
    ("hume", "97fe9008-8584-4d56-8453-bd8c7ead3663"): {
        "description": "Caring mother. Nurturing, attentive, softly insistent — "
                       "maternal warmth without saccharine.",
        "traits": ["warm", "gentle", "mature"],
    },
    ("hume", "43e411b3-b2cc-40da-b742-4abf0e3557b2"): {
        "description": "American lead actress. Versatile adult-female — "
                       "carries dramatic range from warmth to steel.",
        "traits": ["warm", "assertive", "theatrical"],
    },
    ("hume", "a7ecc00a-6fc0-4546-8126-e12cfd8de3bf"): {
        "description": "Alice Bennett. Grounded, articulate woman — "
                       "suits sophisticated, modern roles.",
        "traits": ["crisp", "grounded", "mature"],
    },
    ("hume", "27e8dd8b-7e7c-4c1f-bfb2-c1b016487343"): {
        "description": "Seasoned Midwestern actress. Warm twang, conversational — "
                       "approachable with lived-in character.",
        "traits": ["warm", "mature", "grounded"],
    },
    ("hume", "faf64860-5d8c-44b2-9fc3-88717d307ce8"): {
        "description": "Classical film actress. Mid-century diction, stylised pitch — "
                       "period-piece heroine energy.",
        "traits": ["theatrical", "mature", "posh"],
    },
    ("hume", "fcd2297b-44dd-4115-97af-a13297afb8cb"): {
        "description": "Classical film actor. Mid-century trained male — "
                       "crisp consonants, cinematic projection.",
        "traits": ["theatrical", "commanding", "mature"],
    },
    ("hume", "3f636d17-44c7-4872-93d1-0c8f51c916a3"): {
        "description": "Charming cowgirl. Warm drawl, wink in the delivery — "
                       "flirty or rogue-heroine lines.",
        "traits": ["warm", "playful"],
    },
    ("hume", "4b305eef-58eb-455c-a154-be40c3129d0b"): {
        "description": "Charismatic politician man. Persuasive, rhythmic, controlled — "
                       "pulpit cadence; feels rehearsed on purpose.",
        "traits": ["commanding", "assertive", "theatrical"],
    },
    ("hume", "f4703974-b6a1-45c8-ac72-72ea06e3dd43"): {
        "description": "Steve Frisch. Bright, a bit nasal American male — "
                       "reads as sharp, clever, TV-host adjacent.",
        "traits": ["nasal", "bright", "casual"],
    },
    ("hume", "d8ab67c6-953d-4bd8-9370-8fa53a0f1453"): {
        "description": "Colton Rivers. Rugged, mid-low American male — "
                       "action-lead or late-night-host baseline.",
        "traits": ["grounded", "deep", "mature"],
    },
    ("hume", "82a76fb8-3524-4e87-9265-9795c8e4ede6"): {
        "description": "Male protagonist. Clean, capable leading-man — "
                       "default heroic register.",
        "traits": ["grounded", "assertive", "commanding"],
    },
    ("hume", "6a42908a-f332-4c39-a93a-98c7d6017f12"): {
        "description": "Tough guy. Low, clipped, a little menacing — "
                       "fits enforcers, hardened vets.",
        "traits": ["deep", "menacing", "assertive"],
    },
    ("hume", "15f594d3-0683-4585-b799-ce12e939a0e2"): {
        "description": "Brooding intellectual man. Low, deliberate, darkly reflective — "
                       "suits introspective or cynical monologue.",
        "traits": ["deep", "dark", "serious"],
    },
    ("hume", "89989d92-1de8-4e5d-97e4-23cd363e9788"): {
        "description": "Opinionated guy. Pushy, emphatic, a bit abrasive — "
                       "argumentative or combative lines.",
        "traits": ["assertive", "energetic"],
    },
    ("hume", "9388af0d-4d33-4cdf-8b0a-f003b6cf9455"): {
        "description": "Grizzled New Yorker. Weathered, brash, mid-low — "
                       "working-class NYC stock character.",
        "traits": ["mature", "casual", "assertive"],
    },
    ("hume", "a3d1e23c-403e-423b-aeae-c568ad0bccba"): {
        "description": "California frat bro. Bright, upspeak, casual surf cadence — "
                       "young-dude / jock energy.",
        "traits": ["bright", "youthful", "casual", "playful"],
    },
    ("hume", "a5b1def0-16a5-4fcc-bfa8-2a0de2e35d93"): {
        "description": "Unserious TV host. Bright, quippy, on-mic performer — "
                       "late-night vibe, never quite sincere.",
        "traits": ["bright", "playful", "theatrical"],
    },
    ("hume", "cb1a4fae-dad5-4729-bd73-a43f570b9117"): {
        "description": "Live comedian. Performative timing, audience-facing — "
                       "punchline cadence baked in.",
        "traits": ["theatrical", "playful", "energetic"],
    },
    ("hume", "28441f64-64a0-4df4-9bd2-478850ee5fac"): {
        "description": "New York comedian guy. Sardonic, neurotic, rapid — "
                       "stand-up rhythm; observational bite.",
        "traits": ["nasal", "energetic", "playful"],
    },
    ("hume", "c5be03fa-09cc-4fc3-8852-7f5a32b5606c"): {
        "description": "Sitcom guy. Bright, reactive, stage-adjacent — "
                       "multicam-comedy timing.",
        "traits": ["bright", "energetic", "theatrical"],
    },
    ("hume", "5bbc32c1-a1f6-44e8-bedb-9870f23619e2"): {
        "description": "Sitcom girl. Chirpy, reactive, occasionally deadpan — "
                       "friend-group lead archetype.",
        "traits": ["bright", "energetic", "playful"],
    },
    ("hume", "6b69954e-6c9a-4ade-ad03-f73e116e1eae"): {
        "description": "Male Australian naturalist. Enthused, full-throated — "
                       "Irwin-style wildlife-encounter narration.",
        "traits": ["energetic", "theatrical", "narrator"],
    },
    ("hume", "d8de3d55-9fcc-4aad-ac93-131141602717"): {
        "description": "Cheerful Irishman. Lilted, bright, warm — "
                       "pub-raconteur / friendly-stranger energy.",
        "traits": ["warm", "bright", "cheerful"],
    },
    ("hume", "dd39f331-a857-4c20-908a-1f0c56b0a79b"): {
        "description": "Cheerful Canadian. Bright, polite, lightly upspeaked — "
                       "earnest middle-of-the-road warmth.",
        "traits": ["warm", "bright", "cheerful"],
    },
    ("hume", "a48360cb-14f3-460c-93f2-b38deb45400b"): {
        "description": "Scottish guy. Burred accent, grounded mid-register — "
                       "reads as direct, unpretentious.",
        "traits": ["warm", "grounded", "casual"],
    },
    ("hume", "2ae087da-ab61-4455-b095-4e926f0e75a2"): {
        "description": "Yorkshire chap. Blunt regional English — "
                       "working-class northern texture, no polish.",
        "traits": ["grounded", "casual", "mature"],
    },
    ("hume", "36e7572e-f5b2-477e-ae61-4400dbeaa034"): {
        "description": "Excitable British naturalist. Animated RP-ish male — "
                       "Attenborough-successor energy, more frenetic.",
        "traits": ["energetic", "theatrical", "narrator", "posh"],
    },
    ("hume", "2bc0fca6-d591-4855-abef-ec048a385e8f"): {
        "description": "Pirate captain. Gruff theatrical baritone — "
                       "stage-swagger scenes; leans into parody.",
        "traits": ["theatrical", "playful", "commanding"],
    },
    ("hume", "e7024495-03e7-4e8b-8b22-27c54ee25ffa"): {
        "description": "Wise wizard. Measured, grandfatherly baritone — "
                       "archetypal fantasy-mentor delivery.",
        "traits": ["warm", "mature", "gravitas"],
    },
    ("hume", "a1e5674e-3ef1-4394-913c-d4cd70b96801"): {
        "description": "Medieval peasant man. Earthy, gravelly, low-register — "
                       "rustic NPC / serf delivery.",
        "traits": ["grounded", "mature", "dark"],
    },
    ("hume", "a6984261-4b9f-492c-a5fd-9ddbe14039c4"): {
        "description": "Medieval peasant woman. Earthy, weathered female — "
                       "rustic stock character with folk texture.",
        "traits": ["grounded", "mature"],
    },
    ("hume", "27019e54-59c4-4400-a51c-7e5fd2142029"): {
        "description": "Old-timey English priest. Hushed, sonorous, reverent — "
                       "sermonic cadence with archaic feel.",
        "traits": ["soft", "gravitas", "posh"],
    },
    ("hume", "44cb3a51-07b4-4934-83fd-9d9e8d363ce6"): {
        "description": "Dungeon Master. Theatrical, relishing every syllable — "
                       "narration-as-performance; leans campy.",
        "traits": ["theatrical", "commanding", "playful"],
    },
    ("hume", "2c0e2c10-ac19-4aac-93d0-29c385d7364e"): {
        "description": "Ghost with unfinished business. Hollow, rasped, melancholy — "
                       "spectral delivery; unresolved grief.",
        "traits": ["dark", "melancholy", "soft"],
    },
    ("hume", "39e3bc67-3cac-477e-910c-0bb91f3191a8"): {
        "description": "Comical vampire. Faux-aristocratic, arched, performative — "
                       "parody horror; Lugosi-adjacent.",
        "traits": ["theatrical", "playful", "posh"],
    },
    ("hume", "f4aade2d-50d1-4854-a6ee-494f48458eab"): {
        "description": "Unserious vampire. Camp, drawn-out, hammy — "
                       "comedic horror; knowingly ridiculous.",
        "traits": ["theatrical", "playful"],
    },
    ("hume", "b89de4b1-3df6-4e4f-a054-9aed4351092d"): {
        "description": "Campfire narrator. Hushed, close, storyteller — "
                       "works for ghost stories or folklore tellings.",
        "traits": ["soft", "intimate", "narrator"],
    },
    ("hume", "5cad536a-3013-4f01-8390-d6d405d266a9"): {
        "description": "Literature professor. Dry, articulate, mid-weight — "
                       "academic cadence, lightly amused by itself.",
        "traits": ["crisp", "mature", "posh"],
    },
    ("hume", "9e068547-5ba4-4c8e-8e03-69282a008f04"): {
        "description": "Male English actor. Trained RP — "
                       "stage-to-screen versatility; projects easily.",
        "traits": ["theatrical", "posh", "mature"],
    },
    ("hume", "203d3e34-e50b-48ab-a782-835fa39c36c6"): {
        "description": "Nasal podcast host. Distinctly nasal male — "
                       "mumble-core indie vibe; signature character.",
        "traits": ["nasal", "casual"],
    },
    ("hume", "55813df9-fdbb-4ec2-a539-1b91fd750ca6"): {
        "description": "Sad old British man. Thin, wistful, mid-low — "
                       "melancholic reminiscence.",
        "traits": ["melancholy", "mature", "soft"],
    },
    ("hume", "7f633ac4-8181-4e0d-99e1-11a4ef033691"): {
        "description": "Terrence Bentley. Refined older British male — "
                       "butler / elder-statesman delivery.",
        "traits": ["posh", "mature", "calm"],
    },
    ("hume", "522fc367-961f-4817-8929-81f433b4afe9"): {
        "description": "Sebastian Lockwood. Cultured young-to-mid British male — "
                       "reads as smooth, possibly two-faced.",
        "traits": ["posh", "crisp", "assertive"],
    },
    ("hume", "f042c0be-b7cc-4a59-bea2-65f23e12c710"): {
        "description": "Donovan Sinclair. Rich baritone lead male — "
                       "romantic-hero / main-cast presence.",
        "traits": ["deep", "warm", "commanding"],
    },
    ("hume", "ee96fb5f-ec1a-4f41-a9ba-6d119e64c8fd"): {
        "description": "Vince Douglas. Mid American male actor — "
                       "everyman-with-range default.",
        "traits": ["grounded", "mature"],
    },
    ("hume", "2a7b176a-ca45-4ff8-8a65-56f873a5fdc7"): {
        "description": "Awe-inspired guy. Wide-eyed, emphatic — "
                       "reads as perpetually impressed.",
        "traits": ["bright", "energetic", "youthful"],
    },
    ("hume", "7e65fb10-8ef6-4faf-a111-875102d51b25"): {
        "description": "Groovy guy. Loose, laid-back, cadenced — "
                       "70s-DJ or chilled-host vibe.",
        "traits": ["warm", "casual", "playful"],
    },
    ("hume", "da0a369e-7799-40d3-b5c8-3015f198ef57"): {
        "description": "Highly reactive guy. Sharp, alive, big emotional range — "
                       "reacts hard; reads as animated.",
        "traits": ["energetic", "theatrical", "bright"],
    },
    ("hume", "dbfae3fb-560f-4b2e-836c-8546927484ab"): {
        "description": "Anna. Clear, composed adult female — "
                       "modern professional default.",
        "traits": ["crisp", "grounded"],
    },
    ("hume", "5ac595dd-26ce-4898-961a-b19efa9cd491"): {
        "description": "Spanish instructor. Warm Spanish-accented English — "
                       "patient, teacherly.",
        "traits": ["warm", "calm"],
    },
    ("hume", "f8a649d1-0fb6-4168-a1e2-e9ec41937c55"): {
        "description": "French chef. Exaggerated French-accented English — "
                       "parodic culinary character.",
        "traits": ["theatrical", "playful"],
    },
    ("hume", "e722344d-e09a-489d-9f10-b67a28edd35a"): {
        "description": "Turtle guru. Slow, measured, ZEN-parody male — "
                       "comedic mentor, mock-wisdom.",
        "traits": ["soft", "calm", "playful"],
    },
    ("hume", "95f9baac-4512-4edb-a73e-2070784ccc2f"): {
        "description": "Big Dicky. Brash, extra-large American male — "
                       "over-the-top tough-guy parody.",
        "traits": ["deep", "theatrical", "playful"],
    },
    ("hume", "a2cff8f5-1550-4597-9139-63ac4a468b48"): {
        "description": "Colorful fashion influencer. Bright, affected, brand-voice — "
                       "reads as image-first presenter.",
        "traits": ["bright", "theatrical", "energetic"],
    },
    ("hume", "ebba4902-69de-4e01-9846-d8feba5a1a3f"): {
        "description": "TikTok fashion influencer. Rapid, upspeaking, caffeinated — "
                       "short-form-video rhythm.",
        "traits": ["energetic", "youthful", "bright"],
    },
    ("hume", "1a655f88-551e-4633-a502-4c0d668168e8"): {
        "description": "Aunt Tea. Older warm American female — "
                       "chatty-neighbour energy.",
        "traits": ["warm", "mature"],
    },
    ("hume", "35fc083c-a935-40cb-8cfe-805e76009041"): {
        "description": "Friendly Kiwi girl. Bright, polite, Kiwi-accented — "
                       "approachable young adult.",
        "traits": ["bright", "youthful", "cheerful"],
    },
    ("hume", "1200f557-fdf2-4960-8954-6a0591513051"): {
        "description": "Friendly Kiwi guy. Relaxed Kiwi-accented male — "
                       "mid-pitch, casual affability.",
        "traits": ["warm", "casual", "grounded"],
    },
    ("hume", "f33a4a30-d1bc-450e-9174-082dec6aa571"): {
        "description": "Warm Welsh lady. Lilting Welsh female — "
                       "gentle, musical cadence.",
        "traits": ["warm", "gentle"],
    },
    ("hume", "4a9c32ab-e7b5-4439-a7be-54cca5ad9c07"): {
        "description": "Welsh folk storyteller. Measured Welsh-accented narration — "
                       "hearth-and-tale delivery.",
        "traits": ["warm", "narrator", "mature"],
    },
    ("hume", "710e69a0-ea28-4165-8b2f-c3453686b595"): {
        "description": "Indian actor. Confident, warm Indian-accented English male.",
        "traits": ["warm", "commanding"],
    },
    ("hume", "1fe215ab-513c-4fc8-9233-fa64b65073ab"): {
        "description": "Indian actress. Expressive Indian-accented English female.",
        "traits": ["bright", "theatrical"],
    },
    ("hume", "a3cc3538-c557-45e0-ada0-b022937d51c1"): {
        "description": "English children's book narrator. Bright, inviting, stagey — "
                       "picture-book read-aloud.",
        "traits": ["bright", "cheerful", "narrator"],
    },
    ("hume", "6b530c02-5a80-4e60-bb68-f2c171c5029f"): {
        "description": "Expressive girl. Animated, emotional, teen-to-young-adult female.",
        "traits": ["energetic", "youthful", "theatrical"],
    },
    ("hume", "2ca55181-9d21-43b3-9e6e-0cb24a669e6c"): {
        "description": "Unserious movie-trailer narrator. Epic cadence played for laughs.",
        "traits": ["theatrical", "playful"],
    },
    ("hume", "dc6f3593-4ae1-46eb-9121-b872ad7ba1a0"): {
        "description": "Wrestling announcer. Roaring, emphatic, hype-build male.",
        "traits": ["theatrical", "commanding", "energetic"],
    },
    ("hume", "a5e24ed0-7923-43c9-b26e-c77f836e4aaa"): {
        "description": "Florence. Composed, classic British female.",
        "traits": ["posh", "mature", "calm"],
    },
    ("hume", "9e1f9e4f-691a-4bb0-b87c-e306a4c838ef"): {
        "description": "Claire. Clear, measured adult female.",
        "traits": ["crisp", "grounded", "mature"],
    },
    ("hume", "abe27a0a-e7d8-489d-9872-116476ad0fcd"): {
        "description": "Camille. Warm, softly French-tinted adult female.",
        "traits": ["warm", "gentle"],
    },
    ("hume", "b21d78f6-c234-4e07-b9fb-524e743333a4"): {
        "description": "Bianca. Confident Italian-accented English female.",
        "traits": ["bright", "assertive"],
    },
    ("hume", "11e1486e-4ab7-4aec-8fab-09efe9759e58"): {
        "description": "Marie Lafleur. Elegant French-accented English female — "
                       "composed, faintly coquettish.",
        "traits": ["posh", "mature"],
    },
    ("hume", "661ab31e-c4d6-4a16-952a-b5806a9b4ad1"): {
        "description": "Fastidious robo-butler. Crisp, faintly mechanical, mannered — "
                       "sci-fi domestic-droid delivery.",
        "traits": ["crisp", "theatrical"],
    },
    ("hume", "921ece15-27c1-4028-b6ac-82d2d93f65c4"): {
        "description": "Sir Spandrel. Fussy British male — "
                       "over-formal, slightly ridiculous.",
        "traits": ["posh", "theatrical", "playful"],
    },
    ("hume", "0366be28-522b-432b-b346-119d5f21c3f2"): {
        "description": "Medieval town crier. Projected, ceremonial — "
                       "public-announcement energy.",
        "traits": ["theatrical", "commanding"],
    },
    ("hume", "9c2fa3e6-7bbf-4e71-8838-3d28f26cc269"): {
        "description": "Friendly troll. Low, rumbling, amiably slow — "
                       "gentle monster archetype.",
        "traits": ["deep", "playful", "warm"],
    },
    ("hume", "a623d3ed-612c-413b-b09f-e0a379a317f0"): {
        "description": "Warm female assistant voice. Pleasant, composed, brand-safe.",
        "traits": ["warm", "calm"],
    },
    ("hume", "8a7dd58c-0cda-4073-9ce6-654184695e99"): {
        "description": "Warm American female. Mid-register friendly default.",
        "traits": ["warm", "grounded"],
    },
    ("hume", "375cd12e-8216-4c6d-8d79-5dfd56fe19f5"): {
        "description": "Mrs. Pembroke. Refined older British female — matron / school-head feel.",
        "traits": ["posh", "mature", "gravitas"],
    },
}


def _label_to_description(voice: dict) -> str:
    """Fallback description when a Hume voice isn't in VOICE_INFO.

    Uses the persona label itself so the textarea isn't empty, but makes
    clear that the user should audition before finalising.
    """
    label = voice.get("label") or voice.get("id") or "this voice"
    return f"{label} — audition a sample to assess tone and fit; no curated description yet."


def lookup(engine: str, voice: dict) -> dict | None:
    """Return {description, traits} for (engine, voice_id), or a fallback for Hume."""
    info = VOICE_INFO.get((engine, voice.get("id")))
    if info:
        return info
    if engine == "hume":
        return {"description": _label_to_description(voice), "traits": []}
    return None
