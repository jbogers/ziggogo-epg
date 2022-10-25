"""
ZiggoGo EPG

ETSI DVB content descriptor translation module.
Based on https://github.com/tvheadend/tvheadend/blob/master/src/epg.c and
https://www.etsi.org/deliver/etsi_en/300400_300499/300468/01.11.01_60/en_300468v011101p.pdf
"""

import logging

from collections import namedtuple
from typing import List, Optional

DescriptorInfo = namedtuple("DescriptorInfo", ["category_name", "group_name", "weight"])


class ContentDescriptorTranslator:
    """
    Translator for currently known categories used by Ziggo to ETSI DVB standard known categories.
    By adding ETSI DVB standard categories to XMLTV, most TV software can make a proper categorisation of the content.
    """

    # We want a content map that for each known Ziggo keyword gives an ETSI category, but also adds a 'weight' to these.
    # Ideally we write down each category with matching keywords and their weights, then translate this to a better lookup table

    # ETSI lookup map where for each category the known Ziggo keywords are mapped with a weight. The higher the weight value,
    # the more 'important' the mapping is. These can be used to make certain categories and keywords be more likely to be chosen.
    # The end result is a single or limited set of categories to be added to the XMLTV file. Weights used range from 1 to 101.
    # NOTE: Any deviations from the ETSI list are due to the TVHeadend source deviating from that list.
    # IMPORTANT: Weights used in this list are very subjectively chosen and values are selected to give as much unique weights as
    # possible while avoiding collisions. Weight does _not_ indicate the importance of a subject, only how much it says about
    # the content of the program _and_ how much it applies to the ETSI DVB list. Certain categories simply have no real mapping
    # onto the ETSI list and thus get a very low weight, in the hope that a more (subjectively) appropriate category might have
    # a better deciding weight.
    etsi_map = {
        "Movie/Drama": {  # 0x01
            "movie/drama": {  # (general)
                "actie": 1,
                "drama": 10,
                "dramaseries": 11,
                "film": 20,
                "miniseries": 2,
                "misdaaddrama": 3,
                "mysterie": 2,
            },
            "detective/thriller": {
                "thriller": 45,
            },
            "adventure/western/war": {
                "avontuur": 10,
                "oorlog": 10,
                "western": 50,
            },
            "science fiction/fantasy/horror": {
                "fantasy": 50,
                "horror": 50,
                "sciencefiction": 50,
            },
            "comedy": {
                "komedie": 48,
                "romantische komedie": 40,
                "sitcoms": 55,
                "zwarte komedie": 55,
            },
            "soap/melodrama/folkloric": {
                "soap": 50,
            },
            "romance": {
                "romantiek": 60,
            },
            "serious/classical/religious/historical movie/drama": {
                "historisch drama": 50,
                "klassieke geschiedenis": 50,
            },
            "adult movie/drama": {},
        },
        "News/Current affairs": {  # 0x02
            "news/current affairs": {  # (general)
                "actualiteit": 10,
                "actualiteitenprogramma's": 8,
                "misdaad": 1,
            },
            "news/weather report": {
                "nieuws": 60,
                "weer": 80,
            },
            "news magazine": {},
            "documentary": {
                "documentaire": 78,
            },
            "discussion/interview/debate": {
                "debat": 100,
                "interview": 100,
            },
        },
        "Show/Game show": {  # 0x03
            "show/game show": {  # (general)
                "awards": 1,
                "entertainment": 4,
                "event": 1,
                "standup komedie": 30,
                "veiling": 10,
            },
            "game show/quiz/contest": {
                "reality-competitie": 50,
                "spelshow": 62,
            },
            "variety show": {
                "variété": 40,
            },
            "talk show": {
                "sporttalkshow": 50,
                "talkshow": 85,
            },
        },
        "Sports": {  # 0x04
            "sports": {  # (general)
                "extreme sporten": 10,
                "sport": 12,
                "golf": 50,
                "stierenvechten": 50,
                "vliegsport": 10,
                "wielrennen": 50,
            },
            "special events (olympic games, world cup, etc.)": {
                "multisportevenement": 10,
                "olympische spelen": 100,
            },
            "sports magazines": {},
            "football/soccer": {
                "american football": 100,
                "voetbal": 100,
            },
            "tennis/squash": {
                "tennis": 100,
            },
            "team sports (excluding football)": {
                "rugby": 80,
                "rugby league": 100,
            },
            "athletics": {},
            "motor sport": {
                "motorsport": 100,
            },
            "water sport": {
                "duiken": 50,
                "varen": 30,
            },
            "winter sports": {
                "skiën": 50,
            },
            "equestrian": {},
            "martial sports": {},
        },
        "Children's/Youth programmes": {  # 0x05
            "children's / youth programs": {  # (general)
                "kids en familie": 50,
                "kinderen": 51,
            },
            "pre-school children's programs": {},
            "entertainment programs for 6 to1 4": {},
            "entertainment programs for 10 to 16": {},
            "informational/educational/school programs": {},
            "cartoons/puppets": {
                "animatie": 60,
                "anime": 60,
            },
        },
        "Music/Ballet/Dance": {  # 0x06
            "music/ballet/dance": {  # (general)
                "muziek": 19,
            },
            "rock/pop": {},
            "serious music/classical music": {},
            "folk/traditional music": {},
            "jazz": {},
            "musical/opera": {
                "musical": 50,
                "opera": 50,
            },
            "ballet": {
                "ballet": 100,
            },
        },
        "Arts/Culture (without music)": {  # 0x07
            "arts/culture (without music)": {  # (general)
                "beeldende kunst": 30,
                "bloemlezing": 10,
                "kunstnijverheid": 30,
            },
            "performing arts": {
                "cheerleading": 20,
                "dans": 80,
                "podiumkunsten": 75,
                "theater": 50,
            },
            "fine arts": {},
            "religion": {
                "religie": 50,
            },
            "popular culture/traditional arts": {},
            "literature": {
                "boeken & literatuur": 101,
            },
            "film/cinema": {},
            "experimental film/video": {},
            "broadcasting/press": {},
            "new media": {},
            "arts magazines/culture magazines": {},
            "fashion": {
                "mode": 75,
            },
        },
        "Social/Political issues/Economics": {  # 0x08
            "social/political issues/economics": {  # (general)
                "business & financial": 30,
                "consumentenprogramma's": 1,
                "goede doelen": 10,
                "lhbti": 1,
                "opvoeden": 5,
                "politiek": 50,
                "politieke satire": 1,
                "recht": 21,
                "samenleving": 20,
            },
            "magazines/reports/documentary": {
                "docudrama": 20,
                "docusoap": 20,
                "paranormaal": 1,
            },
            "economics/social advisory": {
                "zelfhulp": 30,
            },
            "remarkable people": {},
        },
        "Education/Science/Factual topics": {  # 0x09
            "education/science/factual topics": {  # (general)
                "amerikaanse geschiedenis": 20,
                "biografie": 1,
                "educatie": 50,
                "geschiedenis": 20,
                "militair": 1,
                "reality": 3,
                "verzamelen": 1,
                "wereldgeschiedenis": 20,
                "wetenschap": 10,
            },
            "nature/animals/environment": {
                "dieren": 75,
                "landbouw": 10,
                "natuur": 21,
                "natuur en milieu": 40,
            },
            "technology/natural sciences": {
                "computers": 50,
                "technologie": 50,
            },
            "medicine/physiology/psychology": {
                "medisch": 32,
            },
            "foreign countries/expeditions": {},
            "social/spiritual sciences": {},
            "further education": {},
            "languages": {},
        },
        "Leisure hobbies": {  # 0x0A
            "leisure hobbies": {  # (general)
                "fietsen": 10,
                "gamen": 10,
                "outdoor": 10,
                "vissen": 1,
            },
            "tourism/travel": {
                "reizen": 55,
            },
            "handicraft": {
                "bouwen en verbouwen": 12,
                "doe-het-zelf": 10,
            },
            "motoring": {
                "auto's": 12,
                "motors": 40,
            },
            "fitness and health": {
                "exercise": 50,
                "fit en gezond": 50,
                "gezondheid": 31,
            },
            "cooking": {
                "culinair": 80,
            },
            "advertisement / shopping": {},
            "gardening": {
                "home & garden": 42,
            },
        },
    }

    lookup_table = None

    def __init__(self):
        self._translate_etsi_map_to_lookup_table()

    @classmethod
    def _translate_etsi_map_to_lookup_table(cls):
        """Translate the ETSI map to a lookup table that is keyed on the ZiggoGo descriptor"""

        if cls.lookup_table is not None:
            # Lookup table transformation already done, skip
            return

        cls.lookup_table = {}

        for group_name, group in cls.etsi_map.items():
            for category_name, descriptor_weights in group.items():
                for descriptor, weight in descriptor_weights.items():
                    cls.lookup_table[descriptor.lower()] = DescriptorInfo(
                        category_name=category_name, group_name=group_name, weight=weight
                    )

    def get_dvb_category(self, program_name: str, categories: List[str]) -> Optional[str]:
        """
        Do a best guess on the appropriate ETSI DVB category of the program based on the ZiggoGo category list.
        Uses the weighted etsi_map to determine the most likely description by scoring each of the ZiggoGo categories
        from the map. First the best matching group(s) is(/are) determined and then the highest scoring final category is
        selected.

        :param program_name: Currently unused. May be used in the future to better guess the proper category.
        :param categories: List of ZiggoGo categories assigned to the program
        :return: The best guess for the ETSI DVB category or None if there is no match
        """
        group_scores = {}
        category_scores_by_group = {}

        # Calculate score(s)
        for category in categories:
            category = category.lower()
            if category not in self.lookup_table:
                # Skip unknown category
                continue

            descriptor_info = self.lookup_table[category]
            if descriptor_info.group_name not in group_scores:
                group_scores[descriptor_info.group_name] = 0
                category_scores_by_group[descriptor_info.group_name] = {}
            group_scores[descriptor_info.group_name] += descriptor_info.weight

            if descriptor_info.category_name not in category_scores_by_group[descriptor_info.group_name]:
                category_scores_by_group[descriptor_info.group_name][descriptor_info.category_name] = 0
            category_scores_by_group[descriptor_info.group_name][descriptor_info.category_name] += descriptor_info.weight

        if not group_scores:
            # No matches found at all, give up
            return None

        # Create candidate list out of the highest scoring group(s)
        group_high_score = max(group_scores.values())
        candidate_list = {}
        for group_name, score in group_scores.items():
            if score == group_high_score:
                candidate_list.update(category_scores_by_group[group_name])

        # Select highest candidate(s)
        finalists = []
        candidate_high_score = max(candidate_list.values())
        for category_name, score in candidate_list.items():
            if score == candidate_high_score:
                finalists.append(category_name)

        # TODO: Make debug code conditional on debug flag
        if len(finalists) > 1:
            logging.warning(f"{tuple(sorted(categories))} - {sorted(finalists)}: {program_name}")

        # Pick the first result
        return finalists[0]
