from dataclasses import dataclass
from enum import Enum


SYMPTOM_DICTIONARY_VERSION = "7.0"
SUPPORTED_RAG_LANGUAGES = ("english", "urdu", "punjabi")


class SymptomCode(str, Enum):
    # Leaves - rice + cotton
    LEAF_YELLOWING = "LEAF_YELLOWING"
    LEAF_CURLING = "LEAF_CURLING"
    LEAF_BROWN_SPOTS = "LEAF_BROWN_SPOTS"
    LEAF_BLACK_SPOTS = "LEAF_BLACK_SPOTS"
    LEAF_WHITE_SPOTS = "LEAF_WHITE_SPOTS"
    LEAF_LESIONS = "LEAF_LESIONS"
    LEAF_WATER_SOAKED_LESIONS = "LEAF_WATER_SOAKED_LESIONS"
    LEAF_SPINDLE_LESIONS = "LEAF_SPINDLE_LESIONS"
    LEAF_STREAKS = "LEAF_STREAKS"
    LEAF_EDGE_DRYING = "LEAF_EDGE_DRYING"
    LEAF_TIP_DRYING = "LEAF_TIP_DRYING"
    LEAF_DRYING = "LEAF_DRYING"
    LEAF_WILTING = "LEAF_WILTING"
    LEAF_DISCOLORATION = "LEAF_DISCOLORATION"
    LEAF_HOLES = "LEAF_HOLES"

    # Stem / stalk - rice + cotton
    STEM_DARKENING = "STEM_DARKENING"
    STEM_LESIONS = "STEM_LESIONS"
    STEM_WEAKENING = "STEM_WEAKENING"
    STEM_ROTTING = "STEM_ROTTING"
    STEM_BREAKING = "STEM_BREAKING"

    # Whole plant
    PLANT_WILTING = "PLANT_WILTING"
    PLANT_DRYING = "PLANT_DRYING"
    PLANT_YELLOWING = "PLANT_YELLOWING"
    PLANT_DISCOLORATION = "PLANT_DISCOLORATION"
    STUNTED_GROWTH = "STUNTED_GROWTH"
    POOR_GROWTH = "POOR_GROWTH"
    PLANT_DEATH = "PLANT_DEATH"

    # Roots
    ROOT_DARKENING = "ROOT_DARKENING"
    ROOT_ROTTING = "ROOT_ROTTING"
    ROOT_DAMAGE = "ROOT_DAMAGE"

    # Cotton boll
    BOLL_SPOTS = "BOLL_SPOTS"
    BOLL_ROTTING = "BOLL_ROTTING"
    BOLL_DAMAGE = "BOLL_DAMAGE"
    BOLL_DROP = "BOLL_DROP"
    BOLL_OPENING_FAILURE = "BOLL_OPENING_FAILURE"

    # Rice panicle / grain
    PANICLE_DISCOLORATION = "PANICLE_DISCOLORATION"
    PANICLE_DRYING = "PANICLE_DRYING"
    PANICLE_POOR_FILLING = "PANICLE_POOR_FILLING"
    GRAIN_DISCOLORATION = "GRAIN_DISCOLORATION"
    GRAIN_DAMAGE = "GRAIN_DAMAGE"

    # A valid symptom whose semantic similarity to known concepts is too low.
    OTHERS_MAP = "OTHERS_MAP"

    @classmethod
    def _missing_(cls, value):
        # Backward compatibility with older prototype rows.
        if value == "OTHER_SYMPTOM":
            return cls.OTHERS_MAP
        return None


@dataclass(frozen=True)
class SymptomConcept:
    code: SymptomCode
    name: str
    description: str
    plant_part: str | None
    crops: tuple[str, ...]
    distinguishing_rule: str = ""
    parent_code: SymptomCode | None = None

    def semantic_text_for(self, language: str) -> str:
        """Return the concept meaning ONLY in the requested report language.

        V11 deliberately does not merge English, Urdu and Punjabi vectors.
        The API-provided language selects one concept representation so the
        farmer phrase and candidate descriptions live in the same language.
        Crop and plant-part metadata remain deterministic filters only.
        """
        language = language.strip().lower()
        if language == "english":
            return SYMPTOM_RETRIEVAL_ENGLISH[self.code]
        if language == "urdu":
            return SYMPTOM_RETRIEVAL_URDU[self.code]
        if language == "punjabi":
            return SYMPTOM_RETRIEVAL_PUNJABI[self.code]
        raise ValueError(f"Unsupported symptom concept language: {language!r}")

    @property
    def semantic_text(self) -> str:
        # Backward-compatible English view for older scripts.
        return self.semantic_text_for("english")

    @property
    def identity_text(self) -> str:
        return self.semantic_text

    @property
    def retrieval_text(self) -> str:
        return self.semantic_text


BOTH = ("cotton", "rice")
COTTON = ("cotton",)
RICE = ("rice",)


# Controlled semantic knowledge base. These are concepts, not wording aliases.
# The embedding retriever compares the MEANING of original-language farmer symptom
# spans to structured canonical concept descriptions below. No symptom alias table is used.
SYMPTOM_CONCEPTS: dict[SymptomCode, SymptomConcept] = {
    SymptomCode.LEAF_YELLOWING: SymptomConcept(
        SymptomCode.LEAF_YELLOWING,
        "Leaf yellowing",
        "Leaves become specifically yellow or chlorotic, changing from their normal green colour.",
        "leaves",
        BOTH,
        "Use when the observation specifically identifies yellow or chlorotic colour on leaves.",
        SymptomCode.LEAF_DISCOLORATION,
    ),
    SymptomCode.LEAF_CURLING: SymptomConcept(
        SymptomCode.LEAF_CURLING,
        "Leaf curling",
        "Leaves change shape by curling, rolling, twisting, cupping, or folding instead of remaining flat.",
        "leaves",
        BOTH,
        "Use when the main observation is a curled, rolled, twisted, cupped, or folded leaf shape.",
    ),
    SymptomCode.LEAF_BROWN_SPOTS: SymptomConcept(
        SymptomCode.LEAF_BROWN_SPOTS,
        "Brown leaf spots",
        "Discrete localized brown spots or bounded brown patches are visible on the leaf blade.",
        "leaves",
        BOTH,
        "Use when the observation specifically describes discrete localized brown spots or bounded brown patches.",
    ),
    SymptomCode.LEAF_BLACK_SPOTS: SymptomConcept(
        SymptomCode.LEAF_BLACK_SPOTS,
        "Black leaf spots",
        "Black or very dark discrete spots are visible on the leaves.",
        "leaves",
        BOTH,
        "",
    ),
    SymptomCode.LEAF_WHITE_SPOTS: SymptomConcept(
        SymptomCode.LEAF_WHITE_SPOTS,
        "White or pale leaf spots",
        "White, pale, or bleached discrete spots appear on leaf tissue.",
        "leaves",
        BOTH,
        "",
    ),
    SymptomCode.LEAF_LESIONS: SymptomConcept(
        SymptomCode.LEAF_LESIONS,
        "Leaf lesions",
        "A localized damaged or necrotic area is present on a leaf, but no more specific colour, water-soaked, spindle, streak, edge, or tip pattern is stated.",
        "leaves",
        BOTH,
        "Use only for a nonspecific localized damaged or necrotic leaf area when no defining pattern is provided.",
    ),
    SymptomCode.LEAF_WATER_SOAKED_LESIONS: SymptomConcept(
        SymptomCode.LEAF_WATER_SOAKED_LESIONS,
        "Water-soaked leaf lesions",
        "Leaf lesions look wet, translucent, greasy, or water soaked before becoming necrotic.",
        "leaves",
        BOTH,
        "",
    ),
    SymptomCode.LEAF_SPINDLE_LESIONS: SymptomConcept(
        SymptomCode.LEAF_SPINDLE_LESIONS,
        "Spindle-shaped leaf lesions",
        "Elongated spindle or diamond shaped lesions with pointed ends are visible on rice leaves.",
        "leaves",
        RICE,
        "",
    ),
    SymptomCode.LEAF_STREAKS: SymptomConcept(
        SymptomCode.LEAF_STREAKS,
        "Leaf streaks",
        "Long narrow streaks or elongated linear marks run along the leaf.",
        "leaves",
        BOTH,
    ),
    SymptomCode.LEAF_EDGE_DRYING: SymptomConcept(
        SymptomCode.LEAF_EDGE_DRYING,
        "Leaf edge drying",
        "Drying or dead tissue occurs specifically along the side edges or margins of leaves.",
        "leaves",
        BOTH,
        "Use when drying is explicitly localized to the side edge or margin of the leaf blade.",
        SymptomCode.LEAF_DRYING,
    ),
    SymptomCode.LEAF_TIP_DRYING: SymptomConcept(
        SymptomCode.LEAF_TIP_DRYING,
        "Leaf tip drying",
        "Drying or dead tissue occurs specifically at the leaf tip, the terminal end of the blade.",
        "leaves",
        BOTH,
        "Use when drying is explicitly localized to the extreme tip or terminal end of the leaf blade.",
        SymptomCode.LEAF_DRYING,
    ),
    SymptomCode.LEAF_DRYING: SymptomConcept(
        SymptomCode.LEAF_DRYING,
        "Leaf drying",
        "Leaves become dry, desiccated, crisp, or dead over a broad or unspecified part of the blade.",
        "leaves",
        BOTH,
        "Use when drying affects a broad or nonspecific portion of the leaf blade rather than one named small location.",
    ),
    SymptomCode.LEAF_WILTING: SymptomConcept(
        SymptomCode.LEAF_WILTING,
        "Leaf wilting",
        "Leaves wilt: they lose rigidity, become limp, and droop downward.",
        "leaves",
        BOTH,
        "Use when the main observation is loss of leaf rigidity, limpness, or drooping from reduced turgor.",
    ),
    SymptomCode.LEAF_DISCOLORATION: SymptomConcept(
        SymptomCode.LEAF_DISCOLORATION,
        "Leaf discoloration",
        "Leaves have an abnormal colour change, but the specific colour is unknown or not stated.",
        "leaves",
        BOTH,
        "Use only when an abnormal leaf colour is reported but the colour itself is unspecified.",
    ),
    SymptomCode.LEAF_HOLES: SymptomConcept(
        SymptomCode.LEAF_HOLES,
        "Leaf holes or feeding damage",
        "Holes, missing tissue, chewing marks, or visible feeding damage occur on leaves.",
        "leaves",
        BOTH,
    ),
    SymptomCode.STEM_DARKENING: SymptomConcept(
        SymptomCode.STEM_DARKENING,
        "Stem darkening",
        "The stem or stalk itself becomes abnormally dark, brown, or black as a colour change without an explicitly localized lesion or rot.",
        "stem",
        BOTH,
        "Use when the main observation is a broad dark colour change of stem or stalk tissue.",
    ),
    SymptomCode.STEM_LESIONS: SymptomConcept(
        SymptomCode.STEM_LESIONS,
        "Stem lesions",
        "A localized damaged, sunken, necrotic, or discoloured lesion is present on the stem or stalk.",
        "stem",
        BOTH,
        "Use when the main observation is a localized sunken, damaged, or necrotic patch on the stem or stalk.",
    ),
    SymptomCode.STEM_WEAKENING: SymptomConcept(
        SymptomCode.STEM_WEAKENING,
        "Stem weakening",
        "The stem or stalk is unusually weak, fragile, soft, or unable to support the plant normally.",
        "stem",
        BOTH,
    ),
    SymptomCode.STEM_ROTTING: SymptomConcept(
        SymptomCode.STEM_ROTTING,
        "Stem rot",
        "The stem or stalk tissue is visibly rotting, decaying, soft, or decomposed.",
        "stem",
        BOTH,
    ),
    SymptomCode.STEM_BREAKING: SymptomConcept(
        SymptomCode.STEM_BREAKING,
        "Stem breaking or lodging",
        "The stem or stalk breaks, bends over severely, or the plant lodges because structural support is lost.",
        "stem",
        BOTH,
    ),
    SymptomCode.PLANT_WILTING: SymptomConcept(
        SymptomCode.PLANT_WILTING,
        "Whole plant wilting",
        "The plant as a whole becomes limp, drooping, wilted, or loses normal rigidity.",
        "whole plant",
        BOTH,
    ),
    SymptomCode.PLANT_DRYING: SymptomConcept(
        SymptomCode.PLANT_DRYING,
        "Whole plant drying",
        "The whole plant or most above-ground growth becomes dry, desiccated, or dead-looking.",
        "whole plant",
        BOTH,
    ),
    SymptomCode.PLANT_YELLOWING: SymptomConcept(
        SymptomCode.PLANT_YELLOWING,
        "Whole plant yellowing",
        "The plant as a whole is explicitly described as becoming yellow or chlorotic rather than the observation being limited to a named organ such as leaves.",
        "whole plant",
        BOTH,
        "Use when yellow or chlorotic colour is explicitly described for the plant as a whole.",
        SymptomCode.PLANT_DISCOLORATION,
    ),
    SymptomCode.PLANT_DISCOLORATION: SymptomConcept(
        SymptomCode.PLANT_DISCOLORATION,
        "Whole plant discoloration",
        "The whole plant has an abnormal overall colour change, but no specific colour such as yellow is clearly identified.",
        "whole plant",
        BOTH,
        "Use only when the whole plant has an abnormal overall colour but the colour itself is unspecified.",
    ),
    SymptomCode.STUNTED_GROWTH: SymptomConcept(
        SymptomCode.STUNTED_GROWTH,
        "Stunted growth",
        "Plants are noticeably shorter, smaller, or slower growing than expected for their stage.",
        "whole plant",
        BOTH,
    ),
    SymptomCode.POOR_GROWTH: SymptomConcept(
        SymptomCode.POOR_GROWTH,
        "Poor plant growth",
        "Plants show weak, sparse, or generally poor growth without a clearly stated height reduction.",
        "whole plant",
        BOTH,
    ),
    SymptomCode.PLANT_DEATH: SymptomConcept(
        SymptomCode.PLANT_DEATH,
        "Plant death",
        "Individual plants are dead, dying, collapsing, or have completely lost viability.",
        "whole plant",
        BOTH,
    ),
    SymptomCode.ROOT_DARKENING: SymptomConcept(
        SymptomCode.ROOT_DARKENING,
        "Root darkening",
        "Roots show a dark brown or black colour change while the tissue is not described as soft, decayed, decomposed, or rotten.",
        "roots",
        BOTH,
        "Use when roots are described primarily by a dark brown or black colour change without structural decay.",
    ),
    SymptomCode.ROOT_ROTTING: SymptomConcept(
        SymptomCode.ROOT_ROTTING,
        "Root rot",
        "Root tissue is visibly rotten, decayed, soft, decomposed, or breaking down structurally.",
        "roots",
        BOTH,
        "Use when root tissue is explicitly decayed, soft, decomposed, or rotten.",
    ),
    SymptomCode.ROOT_DAMAGE: SymptomConcept(
        SymptomCode.ROOT_DAMAGE,
        "Root damage",
        "Roots show visible injury, breakage, pruning, deformation, or other physical damage.",
        "roots",
        BOTH,
    ),
    SymptomCode.BOLL_SPOTS: SymptomConcept(
        SymptomCode.BOLL_SPOTS,
        "Cotton boll spots or lesions",
        "Cotton bolls show localized spots, bounded lesions, or discrete discoloured patches on the boll surface.",
        "boll",
        COTTON,
        "Use when cotton bolls have localized spots, lesions, or bounded surface patches.",
    ),
    SymptomCode.BOLL_ROTTING: SymptomConcept(
        SymptomCode.BOLL_ROTTING,
        "Cotton boll rot",
        "Cotton bolls show visible rotting, decay, soft breakdown, or decomposition.",
        "boll",
        COTTON,
    ),
    SymptomCode.BOLL_DAMAGE: SymptomConcept(
        SymptomCode.BOLL_DAMAGE,
        "Cotton boll damage",
        "Cotton bolls have physical injury such as holes, tearing, deformation, or damaged tissue without explicit rotting or a simple spot pattern.",
        "boll",
        COTTON,
        "Use when the main observation is physical boll injury, holes, tearing, or deformation.",
    ),
    SymptomCode.BOLL_DROP: SymptomConcept(
        SymptomCode.BOLL_DROP,
        "Premature boll drop",
        "Cotton bolls or young fruiting structures fall from the plant before normal maturity.",
        "boll",
        COTTON,
    ),
    SymptomCode.BOLL_OPENING_FAILURE: SymptomConcept(
        SymptomCode.BOLL_OPENING_FAILURE,
        "Boll opening failure",
        "Mature cotton bolls fail to open normally or remain tightly closed when they should open.",
        "boll",
        COTTON,
    ),
    SymptomCode.PANICLE_DISCOLORATION: SymptomConcept(
        SymptomCode.PANICLE_DISCOLORATION,
        "Rice panicle discoloration",
        "A rice panicle changes colour abnormally but is not explicitly described as dry, desiccated, or prematurely straw-coloured from drying.",
        "panicle",
        RICE,
        "Use when the main observation is an abnormal panicle colour and moisture loss is not stated.",
    ),
    SymptomCode.PANICLE_DRYING: SymptomConcept(
        SymptomCode.PANICLE_DRYING,
        "Rice panicle drying",
        "Rice panicles, branches, or heads become dry or desiccated prematurely before normal maturity.",
        "panicle",
        RICE,
        "Use when the panicle is explicitly described as dry, desiccated, or prematurely dried.",
    ),
    SymptomCode.PANICLE_POOR_FILLING: SymptomConcept(
        SymptomCode.PANICLE_POOR_FILLING,
        "Poor panicle filling",
        "Rice panicles contain many empty, unfilled, poorly filled, or sterile spikelets.",
        "panicle",
        RICE,
    ),
    SymptomCode.GRAIN_DISCOLORATION: SymptomConcept(
        SymptomCode.GRAIN_DISCOLORATION,
        "Rice grain discoloration",
        "Rice grains or husks show an abnormal colour change while physical deformation, breakage, or shrivelling is not the main observation.",
        "grain",
        RICE,
        "Use when the main observation is an abnormal colour of rice grain or husk.",
    ),
    SymptomCode.GRAIN_DAMAGE: SymptomConcept(
        SymptomCode.GRAIN_DAMAGE,
        "Rice grain damage",
        "Rice grains are physically damaged, malformed, shrivelled, broken, or poorly developed rather than only discoloured.",
        "grain",
        RICE,
        "Use when the main observation is physical grain damage, malformation, breakage, or shrivelling.",
    ),
}




# ---------------------------------------------------------------------------
# V12 retrieval documents
# ---------------------------------------------------------------------------
# These are intentionally SHORT, positive descriptions used ONLY for embedding
# retrieval.  They do not contain exclusion logic such as "not wilting" or
# "not holes", because embedding models can pull those negative terms into the
# vector and make unrelated concepts look similar.
#
# The longer V11 language meanings below are retained for documentation and
# future explanation/reranking, but are NOT embedded by the RAG retriever.

SYMPTOM_RETRIEVAL_ENGLISH: dict[SymptomCode, str] = {
    SymptomCode.LEAF_YELLOWING: "Leaves are turning yellow or pale yellow.",
    SymptomCode.LEAF_CURLING: "Leaves are curling, rolling, twisting, cupping, or folding.",
    SymptomCode.LEAF_BROWN_SPOTS: "Leaves have separate brown spots or brown patches.",
    SymptomCode.LEAF_BLACK_SPOTS: "Leaves have separate black or very dark spots.",
    SymptomCode.LEAF_WHITE_SPOTS: "Leaves have separate white, pale, or bleached spots.",
    SymptomCode.LEAF_LESIONS: "Leaves have localized damaged, dead, or necrotic lesions.",
    SymptomCode.LEAF_WATER_SOAKED_LESIONS: "Leaf lesions look wet, translucent, greasy, or water soaked.",
    SymptomCode.LEAF_SPINDLE_LESIONS: "Rice leaves have spindle-shaped or diamond-shaped lesions with pointed ends.",
    SymptomCode.LEAF_STREAKS: "Leaves have long narrow streaks, stripes, or linear marks.",
    SymptomCode.LEAF_EDGE_DRYING: "Leaf edges or margins are drying or becoming dead.",
    SymptomCode.LEAF_TIP_DRYING: "Leaf tips are drying or becoming dead.",
    SymptomCode.LEAF_DRYING: "Leaves are drying, becoming crisp, or losing moisture.",
    SymptomCode.LEAF_WILTING: "Leaves are wilting, becoming limp, or drooping downward.",
    SymptomCode.LEAF_DISCOLORATION: "Leaves show a general abnormal colour change.",
    SymptomCode.LEAF_HOLES: "Leaves have holes, missing tissue, chewing marks, or feeding damage.",
    SymptomCode.STEM_DARKENING: "The stem or stalk is becoming dark, brown, or black.",
    SymptomCode.STEM_LESIONS: "The stem or stalk has localized damaged, sunken, or dead lesions.",
    SymptomCode.STEM_WEAKENING: "The stem or stalk is weak, soft, fragile, or unable to support the plant.",
    SymptomCode.STEM_ROTTING: "The stem or stalk is rotting, decaying, softening, or breaking down.",
    SymptomCode.STEM_BREAKING: "The stem is breaking, snapping, bending severely, or causing the plant to lodge.",
    SymptomCode.PLANT_WILTING: "The whole plant is wilting, limp, drooping, or losing rigidity.",
    SymptomCode.PLANT_DRYING: "The whole plant or most of the plant is drying out or becoming dead.",
    SymptomCode.PLANT_YELLOWING: "The whole plant is turning yellow or pale yellow.",
    SymptomCode.PLANT_DISCOLORATION: "The whole plant shows a general abnormal colour change.",
    SymptomCode.STUNTED_GROWTH: "The plant is clearly shorter, smaller, or growing slowly for its stage.",
    SymptomCode.POOR_GROWTH: "The plant is growing weakly, sparsely, or poorly overall.",
    SymptomCode.PLANT_DEATH: "The plant is dead, dying, or has completely collapsed.",
    SymptomCode.ROOT_DARKENING: "Roots are turning brown, black, or unusually dark.",
    SymptomCode.ROOT_ROTTING: "Roots are rotting, decaying, soft, mushy, or breaking down.",
    SymptomCode.ROOT_DAMAGE: "Roots are physically damaged, broken, cut, deformed, or injured.",
    SymptomCode.BOLL_SPOTS: "Cotton bolls have separate spots, lesions, or discoloured patches.",
    SymptomCode.BOLL_ROTTING: "Cotton bolls are rotting, decaying, softening, or breaking down.",
    SymptomCode.BOLL_DAMAGE: "Cotton bolls have holes, tears, deformation, or physical injury.",
    SymptomCode.BOLL_DROP: "Cotton bolls or young fruiting structures are dropping before maturity.",
    SymptomCode.BOLL_OPENING_FAILURE: "Mature cotton bolls remain closed and fail to open normally.",
    SymptomCode.PANICLE_DISCOLORATION: "Rice panicles or heads show an abnormal colour change.",
    SymptomCode.PANICLE_DRYING: "Rice panicles or heads are drying before normal maturity.",
    SymptomCode.PANICLE_POOR_FILLING: "Rice panicles contain many empty, unfilled, or poorly filled spikelets.",
    SymptomCode.GRAIN_DISCOLORATION: "Rice grains or husks show an abnormal colour change.",
    SymptomCode.GRAIN_DAMAGE: "Rice grains are damaged, malformed, shrivelled, broken, or poorly developed.",
}

SYMPTOM_RETRIEVAL_URDU: dict[SymptomCode, str] = {
    SymptomCode.LEAF_YELLOWING: "پتے پیلے یا زرد ہو رہے ہیں۔",
    SymptomCode.LEAF_CURLING: "پتے مڑ، لپٹ، بل کھا یا تہہ ہو رہے ہیں۔",
    SymptomCode.LEAF_BROWN_SPOTS: "پتوں پر الگ الگ بھورے دھبے یا بھورے نشان ہیں۔",
    SymptomCode.LEAF_BLACK_SPOTS: "پتوں پر الگ الگ کالے یا بہت گہرے دھبے ہیں۔",
    SymptomCode.LEAF_WHITE_SPOTS: "پتوں پر الگ الگ سفید یا ہلکے دھبے ہیں۔",
    SymptomCode.LEAF_LESIONS: "پتوں پر محدود خراب، مردہ یا زخمی حصے یا زخم ہیں۔",
    SymptomCode.LEAF_WATER_SOAKED_LESIONS: "پتوں کے زخم گیلے، شفاف، چکنے یا پانی بھرے دکھائی دیتے ہیں۔",
    SymptomCode.LEAF_SPINDLE_LESIONS: "چاول کے پتوں پر نوکیلے سروں والے تکلے یا ہیرے جیسے زخم ہیں۔",
    SymptomCode.LEAF_STREAKS: "پتوں پر لمبی باریک لکیریں، دھاریاں یا لمبے نشان ہیں۔",
    SymptomCode.LEAF_EDGE_DRYING: "پتوں کے کنارے یا حاشیے خشک ہو رہے ہیں۔",
    SymptomCode.LEAF_TIP_DRYING: "پتوں کی نوکیں خشک ہو رہی ہیں۔",
    SymptomCode.LEAF_DRYING: "پتے خشک، بے نمی یا کرکرے ہو رہے ہیں۔",
    SymptomCode.LEAF_WILTING: "پتے مرجھا، ڈھیلے یا نیچے جھک رہے ہیں۔",
    SymptomCode.LEAF_DISCOLORATION: "پتوں کا رنگ غیر معمولی طور پر بدل رہا ہے۔",
    SymptomCode.LEAF_HOLES: "پتوں میں سوراخ، کٹے حصے یا چبانے کے نشان ہیں۔",
    SymptomCode.STEM_DARKENING: "تنا یا ڈنٹھل گہرا، بھورا یا کالا ہو رہا ہے۔",
    SymptomCode.STEM_LESIONS: "تنے یا ڈنٹھل پر محدود خراب، دھنسا ہوا یا مردہ زخم ہے۔",
    SymptomCode.STEM_WEAKENING: "تنا یا ڈنٹھل کمزور، نرم یا نازک ہو رہا ہے۔",
    SymptomCode.STEM_ROTTING: "تنا یا ڈنٹھل گل سڑ، نرم یا خراب ہو رہا ہے۔",
    SymptomCode.STEM_BREAKING: "تنا ٹوٹ، چٹخ یا بہت زیادہ جھک رہا ہے۔",
    SymptomCode.PLANT_WILTING: "پورا پودا مرجھا، ڈھیلا یا جھک رہا ہے۔",
    SymptomCode.PLANT_DRYING: "پورا پودا یا اس کا زیادہ حصہ خشک ہو رہا ہے۔",
    SymptomCode.PLANT_YELLOWING: "پورا پودا پیلا یا زرد ہو رہا ہے۔",
    SymptomCode.PLANT_DISCOLORATION: "پورے پودے کا رنگ غیر معمولی طور پر بدل رہا ہے۔",
    SymptomCode.STUNTED_GROWTH: "پودا معمول سے چھوٹا، کم قد یا آہستہ بڑھ رہا ہے۔",
    SymptomCode.POOR_GROWTH: "پودا مجموعی طور پر کمزور یا خراب بڑھ رہا ہے۔",
    SymptomCode.PLANT_DEATH: "پودا مر رہا ہے یا مر چکا ہے۔",
    SymptomCode.ROOT_DARKENING: "جڑیں بھوری، کالی یا غیر معمولی گہری ہو رہی ہیں۔",
    SymptomCode.ROOT_ROTTING: "جڑیں گل سڑ، نرم یا خراب ہو رہی ہیں۔",
    SymptomCode.ROOT_DAMAGE: "جڑیں ٹوٹی، کٹی، بگڑی یا زخمی ہیں۔",
    SymptomCode.BOLL_SPOTS: "کپاس کے ٹینڈوں پر الگ الگ دھبے، زخم یا رنگ بدلے نشان ہیں۔",
    SymptomCode.BOLL_ROTTING: "کپاس کے ٹینڈے گل سڑ، نرم یا خراب ہو رہے ہیں۔",
    SymptomCode.BOLL_DAMAGE: "کپاس کے ٹینڈوں میں سوراخ، پھٹنا، بگاڑ یا جسمانی چوٹ ہے۔",
    SymptomCode.BOLL_DROP: "کپاس کے ٹینڈے یا کم عمر پھل وقت سے پہلے گر رہے ہیں۔",
    SymptomCode.BOLL_OPENING_FAILURE: "پکے کپاس کے ٹینڈے بند رہتے ہیں اور عام طرح نہیں کھلتے۔",
    SymptomCode.PANICLE_DISCOLORATION: "چاول کی بالیوں یا خوشوں کا رنگ غیر معمولی طور پر بدل رہا ہے۔",
    SymptomCode.PANICLE_DRYING: "چاول کی بالیاں یا خوشے وقت سے پہلے خشک ہو رہے ہیں۔",
    SymptomCode.PANICLE_POOR_FILLING: "چاول کی بالیوں میں بہت سے دانے خالی یا کم بھرے رہ جاتے ہیں۔",
    SymptomCode.GRAIN_DISCOLORATION: "چاول کے دانوں یا چھلکوں کا رنگ غیر معمولی طور پر بدل رہا ہے۔",
    SymptomCode.GRAIN_DAMAGE: "چاول کے دانے خراب، بدشکل، سکڑے یا ٹوٹے ہوئے ہیں۔",
}

SYMPTOM_RETRIEVAL_PUNJABI: dict[SymptomCode, str] = {
    SymptomCode.LEAF_YELLOWING: "پتے پیلے یا زرد ہو رہے نیں۔",
    SymptomCode.LEAF_CURLING: "پتے مڑ، لپٹ، بل کھا یا تہہ ہو رہے نیں۔",
    SymptomCode.LEAF_BROWN_SPOTS: "پتیاں اُتے وکھ وکھ بھورے دھبے یا نشان نیں۔",
    SymptomCode.LEAF_BLACK_SPOTS: "پتیاں اُتے وکھ وکھ کالے یا بہت گہرے دھبے نیں۔",
    SymptomCode.LEAF_WHITE_SPOTS: "پتیاں اُتے وکھ وکھ چٹے یا ہلکے دھبے نیں۔",
    SymptomCode.LEAF_LESIONS: "پتیاں اُتے محدود خراب، مردہ یا زخمی حصے یا زخم نیں۔",
    SymptomCode.LEAF_WATER_SOAKED_LESIONS: "پتیاں دے زخم گیلے، شفاف، چکنے یا پانی بھرے ورگے نیں۔",
    SymptomCode.LEAF_SPINDLE_LESIONS: "چاول دے پتیاں اُتے نوکیلے سِریاں والے تکلے یا ہیرے ورگے زخم نیں۔",
    SymptomCode.LEAF_STREAKS: "پتیاں اُتے لمیاں باریک لکیراں، دھاریاں یا لمبے نشان نیں۔",
    SymptomCode.LEAF_EDGE_DRYING: "پتیاں دے کنارے یا حاشیے سک رہے نیں۔",
    SymptomCode.LEAF_TIP_DRYING: "پتیاں دیاں نوکاں سک رہیاں نیں۔",
    SymptomCode.LEAF_DRYING: "پتے سک، خشک یا کرکرے ہو رہے نیں۔",
    SymptomCode.LEAF_WILTING: "پتے مرجھا، ڈھیلے یا تھلے نوں جھک رہے نیں۔",
    SymptomCode.LEAF_DISCOLORATION: "پتیاں دا رنگ غیر معمولی طور تے بدل رہیا اے۔",
    SymptomCode.LEAF_HOLES: "پتیاں وچ سوراخ، کٹے حصے یا چبن دے نشان نیں۔",
    SymptomCode.STEM_DARKENING: "تنا یا ڈنٹھل گہرا، بھورا یا کالا ہو رہیا اے۔",
    SymptomCode.STEM_LESIONS: "تنے یا ڈنٹھل اُتے محدود خراب، دھنسا ہویا یا مردہ زخم اے۔",
    SymptomCode.STEM_WEAKENING: "تنا یا ڈنٹھل کمزور، نرم یا نازک ہو رہیا اے۔",
    SymptomCode.STEM_ROTTING: "تنا یا ڈنٹھل گل سڑ، نرم یا خراب ہو رہیا اے۔",
    SymptomCode.STEM_BREAKING: "تنا ٹٹ، چٹخ یا بہت زیادہ جھک رہیا اے۔",
    SymptomCode.PLANT_WILTING: "پورا پودا مرجھا، ڈھیلا یا جھک رہیا اے۔",
    SymptomCode.PLANT_DRYING: "پورا پودا یا اوہدا وڈا حصہ سک رہیا اے۔",
    SymptomCode.PLANT_YELLOWING: "پورا پودا پیلا یا زرد ہو رہیا اے۔",
    SymptomCode.PLANT_DISCOLORATION: "پورے پودے دا رنگ غیر معمولی طور تے بدل رہیا اے۔",
    SymptomCode.STUNTED_GROWTH: "پودا معمول توں چھوٹا، گھٹ قد یا ہولی ہولی ودھ رہیا اے۔",
    SymptomCode.POOR_GROWTH: "پودا مجموعی طور تے کمزور یا خراب ودھ رہیا اے۔",
    SymptomCode.PLANT_DEATH: "پودا مر رہیا اے یا مر چکیا اے۔",
    SymptomCode.ROOT_DARKENING: "جڑاں بھوریاں، کالیاں یا غیر معمولی گہریاں ہو رہیاں نیں۔",
    SymptomCode.ROOT_ROTTING: "جڑاں گل سڑ، نرم یا خراب ہو رہیاں نیں۔",
    SymptomCode.ROOT_DAMAGE: "جڑاں ٹٹیاں، کٹیاں، بگڑیاں یا زخمی نیں۔",
    SymptomCode.BOLL_SPOTS: "کپاس دے ٹینڈیاں اُتے وکھ وکھ دھبے، زخم یا رنگ بدلے نشان نیں۔",
    SymptomCode.BOLL_ROTTING: "کپاس دے ٹینڈے گل سڑ، نرم یا خراب ہو رہے نیں۔",
    SymptomCode.BOLL_DAMAGE: "کپاس دے ٹینڈیاں وچ سوراخ، پھٹنا، بگاڑ یا جسمانی چوٹ اے۔",
    SymptomCode.BOLL_DROP: "کپاس دے ٹینڈے یا کچے پھل وقت توں پہلاں ڈگ رہے نیں۔",
    SymptomCode.BOLL_OPENING_FAILURE: "پکے کپاس دے ٹینڈے بند رہندے نیں تے عام طرح نہیں کھلدے۔",
    SymptomCode.PANICLE_DISCOLORATION: "چاول دیاں بالیاں یا خوشیاں دا رنگ غیر معمولی طور تے بدل رہیا اے۔",
    SymptomCode.PANICLE_DRYING: "چاول دیاں بالیاں یا خوشیاں وقت توں پہلاں سک رہیاں نیں۔",
    SymptomCode.PANICLE_POOR_FILLING: "چاول دیاں بالیاں وچ بہت سارے دانے خالی یا گھٹ بھرے رہ جاندے نیں۔",
    SymptomCode.GRAIN_DISCOLORATION: "چاول دے دانیاں یا چھلکیاں دا رنگ غیر معمولی طور تے بدل رہیا اے۔",
    SymptomCode.GRAIN_DAMAGE: "چاول دے دانے خراب، بدشکل، سکڑے یا ٹٹے ہوئے نیں۔",
}

# ---------------------------------------------------------------------------
# Language-specific semantic concept documents for V11 RAG.
# These are NOT phrase aliases. Each canonical symptom has one concise semantic
# definition in Urdu and one in Pakistani Punjabi (Shahmukhi). At runtime the
# report's `language` parameter selects ONLY one language representation.
# ---------------------------------------------------------------------------

SYMPTOM_MEANING_URDU: dict[SymptomCode, str] = {
    SymptomCode.LEAF_YELLOWING: "پتے اپنے عام سبز رنگ سے خاص طور پر پیلے یا زرد ہو جاتے ہیں۔ یہ مرجھانے، سوراخ یا غیر واضح رنگ کی تبدیلی کے لیے نہیں ہے۔",
    SymptomCode.LEAF_CURLING: "پتے اپنی عام چپٹی شکل کے بجائے مڑتے، لپٹتے، بل کھاتے، کپ نما یا تہہ دار ہو جاتے ہیں۔",
    SymptomCode.LEAF_BROWN_SPOTS: "پتوں پر واضح اور الگ الگ بھورے دھبے یا محدود بھورے نشان بنتے ہیں۔ عام رنگت کی تبدیلی یا پورے پتے کے خشک ہونے سے مختلف۔",
    SymptomCode.LEAF_BLACK_SPOTS: "پتوں پر الگ الگ کالے یا بہت گہرے رنگ کے دھبے نظر آتے ہیں۔",
    SymptomCode.LEAF_WHITE_SPOTS: "پتوں پر الگ الگ سفید، ہلکے یا بلیچ جیسے دھبے نظر آتے ہیں۔",
    SymptomCode.LEAF_LESIONS: "پتے پر ایک محدود خراب، مردہ یا زخمی حصہ موجود ہو، لیکن پانی بھرا، تکلا نما، لکیر، کنارہ یا نوک والا خاص نمونہ بیان نہ کیا گیا ہو۔",
    SymptomCode.LEAF_WATER_SOAKED_LESIONS: "پتے کے زخم یا دھبے گیلے، شفاف، چکنے یا پانی بھرے ہوئے دکھائی دیتے ہیں، بعد میں مردہ بھی ہو سکتے ہیں۔",
    SymptomCode.LEAF_SPINDLE_LESIONS: "چاول کے پتے پر لمبا تکلے یا ہیرے جیسا زخم ہو جس کے دونوں سرے نوکیلے ہوں۔",
    SymptomCode.LEAF_STREAKS: "پتوں پر لمبی سیدھی یا پٹی جیسی لکیریں، دھاریاں یا لمبے نشان بنیں۔",
    SymptomCode.LEAF_EDGE_DRYING: "خشکی یا مردہ بافت خاص طور پر پتے کے کناروں یا حاشیے سے شروع ہو، درمیان سے نہیں۔",
    SymptomCode.LEAF_TIP_DRYING: "خشکی یا مردہ بافت خاص طور پر پتے کی آخری نوک یا سرے پر ہو۔",
    SymptomCode.LEAF_DRYING: "پتے کا بڑا یا غیر مخصوص حصہ خشک، بے نمی، کرکرا یا مردہ ہو جائے، صرف نوک یا کنارہ محدود نہ ہو۔",
    SymptomCode.LEAF_WILTING: "پتے اپنی سختی کھو کر نرم، ڈھیلے اور نیچے جھکے ہوئے یا مرجھائے نظر آئیں۔",
    SymptomCode.LEAF_DISCOLORATION: "پتے کا رنگ غیر معمولی بدل گیا ہو لیکن کوئی خاص رنگ جیسے پیلا، بھورا، کالا یا سفید واضح طور پر نہ بتایا گیا ہو۔",
    SymptomCode.LEAF_HOLES: "پتوں میں سوراخ، کٹا ہوا حصہ، چبانے کے نشان یا کھانے سے بافت غائب ہو۔",
    SymptomCode.STEM_DARKENING: "تنا یا ڈنٹھل مجموعی طور پر غیر معمولی گہرا، بھورا یا کالا ہو جائے، مگر کوئی محدود زخم یا سڑن واضح نہ ہو۔",
    SymptomCode.STEM_LESIONS: "تنے یا ڈنٹھل پر محدود دھنسا ہوا، خراب، مردہ یا رنگ بدلا زخم یا نشان موجود ہو۔",
    SymptomCode.STEM_WEAKENING: "تنا یا ڈنٹھل غیر معمولی کمزور، نرم، نازک یا پودے کو سہارا دینے کے قابل نہ رہے۔",
    SymptomCode.STEM_ROTTING: "تنے یا ڈنٹھل کی بافت واضح طور پر سڑ رہی، گل رہی، نرم یا ٹوٹ پھوٹ کا شکار ہو۔",
    SymptomCode.STEM_BREAKING: "تنا ٹوٹ جائے، بہت زیادہ جھک جائے یا پودا ساختی کمزوری کی وجہ سے گر جائے۔",
    SymptomCode.PLANT_WILTING: "پورا پودا مجموعی طور پر ڈھیلا، جھکا ہوا، مرجھایا یا اپنی معمول کی سختی کھو دے۔",
    SymptomCode.PLANT_DRYING: "پورا پودا یا اس کا زیادہ تر بالائی حصہ خشک، بے نمی یا مردہ دکھائی دے۔",
    SymptomCode.PLANT_YELLOWING: "پورا پودا واضح طور پر پیلا یا زرد ہو جائے، صرف کسی ایک عضو جیسے پتے تک محدود نہ ہو۔",
    SymptomCode.PLANT_DISCOLORATION: "پورے پودے کا مجموعی رنگ غیر معمولی بدل جائے لیکن کوئی خاص رنگ واضح نہ بتایا گیا ہو۔",
    SymptomCode.STUNTED_GROWTH: "پودے اپنی عمر یا مرحلے کے مطابق واضح طور پر چھوٹے، کم قد یا معمول سے آہستہ بڑھ رہے ہوں۔",
    SymptomCode.POOR_GROWTH: "پودے کمزور، چھدرے یا مجموعی طور پر خراب بڑھ رہے ہوں، مگر قد میں واضح کمی خاص طور پر بیان نہ ہو۔",
    SymptomCode.PLANT_DEATH: "پودے مر چکے ہوں، مر رہے ہوں، گر کر ختم ہو رہے ہوں یا مکمل طور پر زندہ رہنے کی صلاحیت کھو چکے ہوں۔",
    SymptomCode.ROOT_DARKENING: "جڑوں کا رنگ بھورا یا کالا ہو جائے لیکن جڑیں نرم، گلی سڑی یا ٹوٹتی ہوئی بیان نہ ہوں۔",
    SymptomCode.ROOT_ROTTING: "جڑوں کی بافت واضح طور پر سڑی، گلی، نرم، تحلیل یا ٹوٹ پھوٹ کا شکار ہو۔",
    SymptomCode.ROOT_DAMAGE: "جڑوں میں جسمانی چوٹ، ٹوٹ پھوٹ، کٹاؤ، بگاڑ یا دوسری واضح ساختی نقصان ہو۔",
    SymptomCode.BOLL_SPOTS: "کپاس کے ٹینڈوں کی سطح پر الگ الگ دھبے، محدود زخم یا رنگ بدلے ہوئے نشان موجود ہوں۔",
    SymptomCode.BOLL_ROTTING: "کپاس کے ٹینڈے واضح طور پر گل سڑ رہے ہوں، نرم پڑ رہے ہوں یا ان کی بافت تحلیل ہو رہی ہو۔",
    SymptomCode.BOLL_DAMAGE: "کپاس کے ٹینڈوں میں سوراخ، پھٹنا، بگاڑ یا دوسری جسمانی چوٹ ہو، مگر واضح سڑن بنیادی علامت نہ ہو۔",
    SymptomCode.BOLL_DROP: "کپاس کے ٹینڈے یا کم عمر پھل دار حصے معمول کی پختگی سے پہلے پودے سے گر جائیں۔",
    SymptomCode.BOLL_OPENING_FAILURE: "پختہ کپاس کے ٹینڈے اس وقت بھی بند رہیں جب انہیں عام طور پر کھل جانا چاہیے۔",
    SymptomCode.PANICLE_DISCOLORATION: "چاول کی بالی کا رنگ غیر معمولی بدل جائے لیکن اسے واضح طور پر خشک یا وقت سے پہلے سوکھا ہوا نہ بتایا گیا ہو۔",
    SymptomCode.PANICLE_DRYING: "چاول کی بالی، اس کی شاخیں یا خوشہ معمول کی پختگی سے پہلے واضح طور پر خشک یا بے نمی ہو جائے۔",
    SymptomCode.PANICLE_POOR_FILLING: "چاول کی بالی میں بہت سے دانے خالی، ادھ بھرے، کم بھرے یا بانجھ رہ جائیں۔",
    SymptomCode.GRAIN_DISCOLORATION: "چاول کے دانے یا چھلکے کا رنگ غیر معمولی بدل جائے، جبکہ ٹوٹنا، سکڑنا یا ساختی نقصان بنیادی علامت نہ ہو۔",
    SymptomCode.GRAIN_DAMAGE: "چاول کے دانے جسمانی طور پر خراب، بدشکل، سکڑے، ٹوٹے یا ناقص بنے ہوں، صرف رنگ بدلنا بنیادی مسئلہ نہ ہو۔",
}

SYMPTOM_MEANING_PUNJABI: dict[SymptomCode, str] = {
    SymptomCode.LEAF_YELLOWING: "پتے اپنے عام سبز رنگ توں خاص طور تے پیلے یا زرد ہو جاندے نیں۔ ایہہ مرجھاؤن، سوراخاں یا غیر واضح رنگ دی تبدیلی لئی نہیں۔",
    SymptomCode.LEAF_CURLING: "پتے اپنی عام چپٹی شکل دی بجائے مڑدے، لپٹدے، بل کھاندے، کپ ورگی شکل یا تہہ بنا لیندے نیں۔",
    SymptomCode.LEAF_BROWN_SPOTS: "پتیاں اُتے صاف تے وکھ وکھ بھورے دھبے یا محدود بھورے نشان بن دے نیں۔ ایہہ عام رنگ بدل جان یا پورا پتہ سکن توں وکھ اے۔",
    SymptomCode.LEAF_BLACK_SPOTS: "پتیاں اُتے وکھ وکھ کالے یا بہت گہرے رنگ دے دھبے نظر آندے نیں۔",
    SymptomCode.LEAF_WHITE_SPOTS: "پتیاں اُتے وکھ وکھ چٹے، ہلکے یا بلیچ ورگے دھبے نظر آندے نیں۔",
    SymptomCode.LEAF_LESIONS: "پتے اُتے محدود خراب، مردہ یا زخمی حصہ ہوئے، پر پانی بھریا، تکلا نما، لکیر، کنارہ یا نوک والا خاص نمونہ نہ دسیا گیا ہوئے۔",
    SymptomCode.LEAF_WATER_SOAKED_LESIONS: "پتے دے زخم یا دھبے گیلے، شفاف، چکنے یا پانی نال بھرے ورگے لگن، بعد وچ مردہ وی ہو سکدے نیں۔",
    SymptomCode.LEAF_SPINDLE_LESIONS: "چاول دے پتے اُتے لمبا تکلے یا ہیرے ورگا زخم ہوئے جس دے دونوں سرے نوکیلے ہون۔",
    SymptomCode.LEAF_STREAKS: "پتیاں اُتے لمیاں سیدھیاں یا پٹی ورگیاں لکیراں، دھاریاں یا لمبے نشان بنن۔",
    SymptomCode.LEAF_EDGE_DRYING: "سکاؤ یا مردہ بافت خاص طور تے پتے دے کناریاں توں شروع ہوئے، وچکار توں نہیں۔",
    SymptomCode.LEAF_TIP_DRYING: "سکاؤ یا مردہ بافت خاص طور تے پتے دی آخری نوک یا سرے اُتے ہوئے۔",
    SymptomCode.LEAF_DRYING: "پتے دا وڈا یا غیر مخصوص حصہ سک جائے، بے نمی، کرکرا یا مردہ ہو جائے، صرف نوک یا کنارہ محدود نہ ہوئے۔",
    SymptomCode.LEAF_WILTING: "پتے اپنی سختی کھو کے نرم، ڈھیلے، تھلے نوں جھکے یا مرجھائے ہوئے نظر آون۔",
    SymptomCode.LEAF_DISCOLORATION: "پتے دا رنگ غیر معمولی بدل جائے پر کوئی خاص رنگ جیویں پیلا، بھورا، کالا یا چٹا صاف نہ دسیا گیا ہوئے۔",
    SymptomCode.LEAF_HOLES: "پتیاں وچ سوراخ، کٹیا حصہ، چبن دے نشان یا کھادے جان نال بافت غائب ہوئے۔",
    SymptomCode.STEM_DARKENING: "تنا یا ڈنٹھل مجموعی طور تے غیر معمولی گہرا، بھورا یا کالا ہو جائے، پر محدود زخم یا سڑن صاف نہ ہوئے۔",
    SymptomCode.STEM_LESIONS: "تنے یا ڈنٹھل اُتے محدود دھنسا ہویا، خراب، مردہ یا رنگ بدلیا زخم یا نشان ہوئے۔",
    SymptomCode.STEM_WEAKENING: "تنا یا ڈنٹھل غیر معمولی کمزور، نرم، نازک یا پودے نوں سہارا دین جوگا نہ رہے۔",
    SymptomCode.STEM_ROTTING: "تنے یا ڈنٹھل دی بافت صاف طور تے سڑ رہی، گل رہی، نرم یا ٹٹ رہی ہوئے۔",
    SymptomCode.STEM_BREAKING: "تنا ٹٹ جائے، بہت زیادہ جھک جائے یا ساختی کمزوری کرکے پودا ڈگ پئے۔",
    SymptomCode.PLANT_WILTING: "پورا پودا مجموعی طور تے ڈھیلا، جھکیا، مرجھایا یا اپنی عام سختی کھو بیٹھے۔",
    SymptomCode.PLANT_DRYING: "پورا پودا یا اوہدا زیادہ تر اوپرلا حصہ سکیا، بے نمی یا مردہ ورگا نظر آوے۔",
    SymptomCode.PLANT_YELLOWING: "پورا پودا صاف طور تے پیلا یا زرد ہو جائے، صرف پتیاں یا ہور اک عضو تک محدود نہ ہوئے۔",
    SymptomCode.PLANT_DISCOLORATION: "پورے پودے دا مجموعی رنگ غیر معمولی بدل جائے پر کوئی خاص رنگ صاف نہ دسیا گیا ہوئے۔",
    SymptomCode.STUNTED_GROWTH: "پودے اپنی عمر یا مرحلے دے حساب نال صاف طور تے چھوٹے، گھٹ قد یا معمول توں ہولی ودھ رہے ہون۔",
    SymptomCode.POOR_GROWTH: "پودے کمزور، چھدرے یا مجموعی طور تے خراب ودھ رہے ہون، پر قد دی واضح کمی خاص طور تے نہ دسی گئی ہوئے۔",
    SymptomCode.PLANT_DEATH: "پودے مر چکے ہون، مر رہے ہون، ڈگ کے ختم ہو رہے ہون یا پوری طرح زندہ رہن دی صلاحیت کھو چکے ہون۔",
    SymptomCode.ROOT_DARKENING: "جڑاں دا رنگ بھورا یا کالا ہو جائے پر جڑاں نرم، گلیاں سڑیاں یا ٹٹدیاں ہوئیاں نہ دسیاں گئیاں ہون۔",
    SymptomCode.ROOT_ROTTING: "جڑاں دی بافت صاف طور تے سڑی، گلی، نرم، تحلیل یا ٹٹ پھٹ دا شکار ہوئے۔",
    SymptomCode.ROOT_DAMAGE: "جڑاں وچ جسمانی چوٹ، ٹٹ پھٹ، کٹاؤ، بگاڑ یا ہور صاف ساختی نقصان ہوئے۔",
    SymptomCode.BOLL_SPOTS: "کپاس دے ٹینڈیاں دی سطح اُتے وکھ وکھ دھبے، محدود زخم یا رنگ بدلے نشان ہون۔",
    SymptomCode.BOLL_ROTTING: "کپاس دے ٹینڈے صاف طور تے گل سڑ رہے ہون، نرم پے رہے ہون یا اوہناں دی بافت ٹٹ رہی ہوئے۔",
    SymptomCode.BOLL_DAMAGE: "کپاس دے ٹینڈیاں وچ سوراخ، پھٹنا، بگاڑ یا ہور جسمانی چوٹ ہوئے، پر صاف سڑن بنیادی علامت نہ ہوئے۔",
    SymptomCode.BOLL_DROP: "کپاس دے ٹینڈے یا کچے پھل والے حصے عام پکاوٹ توں پہلاں پودے توں ڈگ پین۔",
    SymptomCode.BOLL_OPENING_FAILURE: "پکے کپاس دے ٹینڈے اوہدوں وی بند رہن جدوں اوہناں نوں عام طور تے کھل جانا چاہیدا اے۔",
    SymptomCode.PANICLE_DISCOLORATION: "چاول دی بالی دا رنگ غیر معمولی بدل جائے پر اوہنوں صاف طور تے سکیا یا وقت توں پہلاں سوکیا نہ دسیا گیا ہوئے۔",
    SymptomCode.PANICLE_DRYING: "چاول دی بالی، اوہ دیاں شاخاں یا خوشہ عام پکاوٹ توں پہلاں صاف طور تے سک جائے یا بے نمی ہو جائے۔",
    SymptomCode.PANICLE_POOR_FILLING: "چاول دی بالی وچ بہت سارے دانے خالی، ادھ بھرے، گھٹ بھرے یا بانجھ رہ جان۔",
    SymptomCode.GRAIN_DISCOLORATION: "چاول دے دانے یا چھلکے دا رنگ غیر معمولی بدل جائے، جدکہ ٹٹنا، سکڑنا یا ساختی نقصان بنیادی علامت نہ ہوئے۔",
    SymptomCode.GRAIN_DAMAGE: "چاول دے دانے جسمانی طور تے خراب، بدشکل، سکڑے، ٹٹے یا ناقص بنے ہون، صرف رنگ بدلنا بنیادی مسئلہ نہ ہوئے۔",
}


def _validate_language_catalog() -> None:
    expected = set(SYMPTOM_CONCEPTS)
    for language, catalog in (
        ("english_retrieval", SYMPTOM_RETRIEVAL_ENGLISH),
        ("urdu_retrieval", SYMPTOM_RETRIEVAL_URDU),
        ("punjabi_retrieval", SYMPTOM_RETRIEVAL_PUNJABI),
        ("urdu_detail", SYMPTOM_MEANING_URDU),
        ("punjabi_detail", SYMPTOM_MEANING_PUNJABI),
    ):
        missing = expected - set(catalog)
        extra = set(catalog) - expected
        if missing or extra:
            raise RuntimeError(
                f"Invalid {language} symptom catalog: "
                f"missing={[x.value for x in sorted(missing, key=lambda x: x.value)]}, "
                f"extra={[x.value for x in sorted(extra, key=lambda x: x.value)]}"
            )


_validate_language_catalog()


# A concise compatibility mapping used by UI/report code that only needs a
# human-readable label. Semantic retrieval uses SYMPTOM_CONCEPTS above.
SYMPTOM_CODES: dict[SymptomCode, str] = {
    code: concept.name for code, concept in SYMPTOM_CONCEPTS.items()
}
SYMPTOM_CODES[SymptomCode.OTHERS_MAP] = "Other / unmapped symptom"
