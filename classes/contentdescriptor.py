"""
ZiggoGo EPG

ETSI DVB content descriptor translation module.
Based on https://github.com/tvheadend/tvheadend/blob/master/src/epg.c and
https://www.etsi.org/deliver/etsi_en/300400_300499/300468/01.11.01_60/en_300468v011101p.pdf
"""

import logging

from collections import namedtuple
from enum import Enum
from typing import List

DescriptorInfo = namedtuple("DescriptorInfo", ["category_name", "group_name", "mapping_type"])


class MappingType(Enum):
    DIRECT = 1
    GROUP = 2
    ONLY = 3


class ContentDescriptorTranslator:
    """
    Translator for currently known categories used by Ziggo to ETSI DVB standard known categories.
    By adding ETSI DVB standard categories to XMLTV, most TV software can make a proper categorisation of the content.
    """

    # ETSI lookup map where for each category the known Ziggo keywords are mapped with a 'suggested' mapping type. These are:
    # - DIRECT: Simple map to the keyword, always applied
    # - GROUP: If there are no other direct keywords in the same group, this is applied
    # - ONLY: Only used if no other keywords of any higher grade were mapped in any group
    #
    # NOTE: Any deviations from the ETSI list are due to the TVHeadend source deviating from that list.
    # IMPORTANT: Mappings used in this list are very subjectively chosen and values are selected to prevent strange combinations
    # due to some Ziggo Go categories being dependent on interpretation. For example, 'misdaad' could apply to a current
    # affairs program about crime (current affairs), or it could apply to a crime movie (fiction).

    etsi_map = {
        "Movie/Drama": {  # 0x01
            "movie/drama": {  # (general)
                "actie": MappingType.GROUP,
                "drama": MappingType.DIRECT,
                "dramaseries": MappingType.DIRECT,
                "film": MappingType.DIRECT,
                "miniseries": MappingType.GROUP,
                "misdaaddrama": MappingType.DIRECT,
            },
            "detective/thriller": {
                "thriller": MappingType.DIRECT,
                "mysterie": MappingType.DIRECT,
            },
            "adventure/western/war": {
                "avontuur": MappingType.DIRECT,
                "oorlog": MappingType.GROUP,
                "western": MappingType.DIRECT,
            },
            "science fiction/fantasy/horror": {
                "fantasy": MappingType.DIRECT,
                "horror": MappingType.DIRECT,
                "sciencefiction": MappingType.DIRECT,
            },
            "comedy": {
                "komedie": MappingType.DIRECT,
                "romantische komedie": MappingType.DIRECT,
                "sitcoms": MappingType.DIRECT,
                "zwarte komedie": MappingType.DIRECT,
            },
            "soap/melodrama/folkloric": {
                "soap": MappingType.DIRECT,
            },
            "romance": {
                "romantiek": MappingType.DIRECT,
            },
            "serious/classical/religious/historical movie/drama": {
                "historisch drama": MappingType.DIRECT,
            },
            "adult movie/drama": {},
        },
        "News/Current affairs": {  # 0x02
            "news/current affairs": {  # (general)
                "actualiteit": MappingType.DIRECT,
                "actualiteitenprogramma's": MappingType.DIRECT,
                "misdaad": MappingType.ONLY,
            },
            "news/weather report": {
                "nieuws": MappingType.DIRECT,
                "weer": MappingType.DIRECT,
            },
            "news magazine": {},
            "documentary": {
                "documentaire": MappingType.DIRECT,
            },
            "discussion/interview/debate": {
                "debat": MappingType.DIRECT,
                "interview": MappingType.DIRECT,
            },
        },
        "Show/Game show": {  # 0x03
            "show/game show": {  # (general)
                "awards": MappingType.DIRECT,
                "entertainment": MappingType.ONLY,
                "event": MappingType.ONLY,
                "standup komedie": MappingType.DIRECT,
                "veiling": MappingType.DIRECT,
            },
            "game show/quiz/contest": {
                "reality-competitie": MappingType.DIRECT,
                "spelshow": MappingType.DIRECT,
            },
            "variety show": {
                "variété": MappingType.DIRECT,
            },
            "talk show": {
                "sporttalkshow": MappingType.DIRECT,
                "talkshow": MappingType.DIRECT,
            },
        },
        "Sports": {  # 0x04
            "sports": {  # (general)
                "extreme sporten": MappingType.DIRECT,
                "sport": MappingType.DIRECT,
                "golf": MappingType.DIRECT,
                "stierenvechten": MappingType.DIRECT,
                "vliegsport": MappingType.DIRECT,
                "wielrennen": MappingType.DIRECT,
            },
            "special events (olympic games, world cup, etc.)": {
                "multisportevenement": MappingType.DIRECT,
                "olympische spelen": MappingType.DIRECT,
            },
            "sports magazines": {},
            "football/soccer": {
                "american football": MappingType.DIRECT,
                "voetbal": MappingType.DIRECT,
            },
            "tennis/squash": {
                "tennis": MappingType.DIRECT,
            },
            "team sports (excluding football)": {
                "rugby": MappingType.DIRECT,
                "rugby league": MappingType.DIRECT,
            },
            "athletics": {},
            "motor sport": {
                "motorsport": MappingType.DIRECT,
            },
            "water sport": {
                "duiken": MappingType.DIRECT,
                "varen": MappingType.DIRECT,
            },
            "winter sports": {
                "skiën": MappingType.DIRECT,
            },
            "equestrian": {},
            "martial sports": {},
        },
        "Children's/Youth programmes": {  # 0x05
            "children's / youth programs": {  # (general)
                "kids en familie": MappingType.DIRECT,
                "kinderen": MappingType.DIRECT,
            },
            "pre-school children's programs": {},
            "entertainment programs for 6 to 14": {},
            "entertainment programs for 10 to 16": {},
            "informational/educational/school programs": {},
            "cartoons/puppets": {
                "animatie": MappingType.DIRECT,
                "anime": MappingType.DIRECT,
            },
        },
        "Music/Ballet/Dance": {  # 0x06
            "music/ballet/dance": {  # (general)
                "muziek": MappingType.DIRECT,
            },
            "rock/pop": {},
            "serious music/classical music": {},
            "folk/traditional music": {},
            "jazz": {},
            "musical/opera": {
                "musical": MappingType.DIRECT,
                "opera": MappingType.DIRECT,
            },
            "ballet": {
                "ballet": MappingType.DIRECT,
            },
        },
        "Arts/Culture (without music)": {  # 0x07
            "arts/culture (without music)": {  # (general)
                "beeldende kunst": MappingType.DIRECT,
                "bloemlezing": MappingType.DIRECT,
                "kunstnijverheid": MappingType.DIRECT,
            },
            "performing arts": {
                "cheerleading": MappingType.DIRECT,
                "dans": MappingType.DIRECT,
                "podiumkunsten": MappingType.DIRECT,
                "theater": MappingType.DIRECT,
            },
            "fine arts": {},
            "religion": {
                "religie": MappingType.DIRECT,
            },
            "popular culture/traditional arts": {},
            "literature": {
                "boeken & literatuur": MappingType.DIRECT,
            },
            "film/cinema": {},
            "experimental film/video": {},
            "broadcasting/press": {},
            "new media": {},
            "arts magazines/culture magazines": {},
            "fashion": {
                "mode": MappingType.DIRECT,
            },
        },
        "Social/Political issues/Economics": {  # 0x08
            "social/political issues/economics": {  # (general)
                "business & financial": MappingType.DIRECT,
                "consumentenprogramma's": MappingType.ONLY,
                "goede doelen": MappingType.DIRECT,
                "lhbti": MappingType.DIRECT,
                "opvoeden": MappingType.DIRECT,
                "politiek": MappingType.DIRECT,
                "politieke satire": MappingType.DIRECT,
                "recht": MappingType.DIRECT,
                "samenleving": MappingType.DIRECT,
            },
            "magazines/reports/documentary": {
                "docudrama": MappingType.DIRECT,
                "docusoap": MappingType.DIRECT,
                "paranormaal": MappingType.DIRECT,
            },
            "economics/social advisory": {
                "zelfhulp": MappingType.DIRECT,
            },
            "remarkable people": {},
        },
        "Education/Science/Factual topics": {  # 0x09
            "education/science/factual topics": {  # (general)
                "amerikaanse geschiedenis": MappingType.DIRECT,
                "biografie": MappingType.DIRECT,
                "educatie": MappingType.DIRECT,
                "geschiedenis": MappingType.DIRECT,
                "klassieke geschiedenis": MappingType.DIRECT,
                "militair": MappingType.ONLY,
                "reality": MappingType.ONLY,
                "verzamelen": MappingType.ONLY,
                "wereldgeschiedenis": MappingType.DIRECT,
                "wetenschap": MappingType.DIRECT,
            },
            "nature/animals/environment": {
                "dieren": MappingType.DIRECT,
                "landbouw": MappingType.DIRECT,
                "natuur": MappingType.DIRECT,
                "natuur en milieu": MappingType.DIRECT,
            },
            "technology/natural sciences": {
                "computers": MappingType.DIRECT,
                "technologie": MappingType.DIRECT,
            },
            "medicine/physiology/psychology": {
                "medisch": MappingType.DIRECT,
            },
            "foreign countries/expeditions": {},
            "social/spiritual sciences": {},
            "further education": {},
            "languages": {},
        },
        "Leisure hobbies": {  # 0x0A
            "leisure hobbies": {  # (general)
                "fietsen": MappingType.DIRECT,
                "gamen": MappingType.DIRECT,
                "outdoor": MappingType.DIRECT,
                "vissen": MappingType.DIRECT,
            },
            "tourism/travel": {
                "reizen": MappingType.DIRECT,
            },
            "handicraft": {
                "bouwen en verbouwen": MappingType.DIRECT,
                "doe-het-zelf": MappingType.DIRECT,
            },
            "motoring": {
                "auto's": MappingType.DIRECT,
                "motors": MappingType.DIRECT,
            },
            "fitness and health": {
                "exercise": MappingType.DIRECT,
                "fit en gezond": MappingType.DIRECT,
                "gezondheid": MappingType.DIRECT,
            },
            "cooking": {
                "culinair": MappingType.DIRECT,
            },
            "advertisement / shopping": {},
            "gardening": {
                "home & garden": MappingType.DIRECT,
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
                for descriptor, mapping_type in descriptor_weights.items():
                    cls.lookup_table[descriptor.lower()] = DescriptorInfo(
                        category_name=category_name, group_name=group_name, mapping_type=mapping_type
                    )

    def get_dvb_categories(self, program_name: str, categories: List[str]) -> List[str]:
        """
        Convert the given categories as good as possible to an ETSI DVB compatible category list.

        :param program_name: Currently used for debugging only. May be used in the future to better guess the proper category.
        :param categories: List of ZiggoGo categories assigned to the program
        :return: List of translated categories. This list may be shorter than the input list
        """
        group_matches = {}

        # Find matches per group
        for category in categories:
            category = category.lower()
            if category not in self.lookup_table:
                # Skip unknown category
                # TODO: Add debug code to print these out
                continue

            descriptor_info = self.lookup_table[category]
            if descriptor_info.group_name not in group_matches:
                group_matches[descriptor_info.group_name] = {}

            if descriptor_info.category_name not in group_matches[descriptor_info.group_name]:
                group_matches[descriptor_info.group_name][descriptor_info.category_name] = descriptor_info.mapping_type
            else:
                # Add the 'smallest' value (the highest match type)
                group_matches[descriptor_info.group_name][descriptor_info.category_name] = MappingType(
                    min(
                        group_matches[descriptor_info.group_name][descriptor_info.category_name].value,
                        descriptor_info.mapping_type.value,
                    )
                )

        if not group_matches:
            # No matches found at all, give up
            return []

        # Copy out mappings
        finalists = []
        for group, dvb_categories in group_matches.items():
            group_finalists = [
                category_name for category_name, mapping_type in dvb_categories.items() if mapping_type is MappingType.DIRECT
            ]
            if not group_finalists:
                # No direct members, fall back to the 'GROUP' mappings
                group_finalists = [
                    category_name for category_name, mapping_type in dvb_categories.items() if mapping_type is MappingType.GROUP
                ]
            finalists.extend(group_finalists)

        if not finalists:
            # No mappings found at all, fall back to the 'ONLY' mappings
            for dvb_categories in group_matches.values():
                for category_name in dvb_categories.keys():
                    finalists.append(category_name)

        return finalists
