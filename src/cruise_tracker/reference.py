"""Reference data: regions, ports and cruise lines the tracker knows about.

Aliases are matched case-insensitively against the port text the sites show,
e.g. "Tokyo (Yokohama), Japan" -> yokohama.
"""

REGIONS = [
    # code, name, is_asia
    ("japan", "日本", True),
    ("korea", "韓國", True),
    ("taiwan", "台灣", True),
    ("southeast_asia", "東南亞", True),
    ("china", "中國／香港", True),
    ("asia_other", "亞洲其他", True),
    ("transpacific", "跨太平洋／移位", False),
    ("alaska", "阿拉斯加", False),
    ("australia", "澳紐", False),
    ("other", "其他", False),
]

# code, name, name_zh, country, region, default_asia, aliases
PORTS = [
    ("keelung", "Keelung", "基隆", "Taiwan", "taiwan", True, ["keelung", "taipei", "jilong"]),
    ("kaohsiung", "Kaohsiung", "高雄", "Taiwan", "taiwan", True, ["kaohsiung"]),
    ("yokohama", "Yokohama", "橫濱（東京）", "Japan", "japan", True, ["yokohama", "tokyo"]),
    ("kobe", "Kobe", "神戶", "Japan", "japan", True, ["kobe"]),
    ("osaka", "Osaka", "大阪", "Japan", "japan", True, ["osaka"]),
    ("fukuoka", "Fukuoka", "福岡（博多）", "Japan", "japan", True, ["fukuoka", "hakata"]),
    ("naha", "Naha", "那霸（沖繩）", "Japan", "japan", True, ["naha", "okinawa"]),
    ("busan", "Busan", "釜山", "South Korea", "korea", True, ["busan", "pusan"]),
    ("incheon", "Incheon", "仁川（首爾）", "South Korea", "korea", True, ["incheon", "seoul"]),
    ("singapore", "Singapore", "新加坡", "Singapore", "southeast_asia", True, ["singapore"]),
    ("hong_kong", "Hong Kong", "香港", "China", "china", False, ["hong kong"]),
    ("shanghai", "Shanghai", "上海", "China", "china", False, ["shanghai"]),
    ("tianjin", "Tianjin", "天津（北京）", "China", "china", False, ["tianjin", "beijing"]),
    ("nagasaki", "Nagasaki", "長崎", "Japan", "japan", False, ["nagasaki"]),
    ("kagoshima", "Kagoshima", "鹿兒島", "Japan", "japan", False, ["kagoshima"]),
    ("ishigaki", "Ishigaki", "石垣島", "Japan", "japan", False, ["ishigaki"]),
    ("jeju", "Jeju", "濟州", "South Korea", "korea", False, ["jeju"]),
    ("bangkok", "Bangkok (Laem Chabang)", "曼谷（林查班）", "Thailand", "southeast_asia", False, ["laem chabang", "bangkok"]),
    ("ho_chi_minh", "Ho Chi Minh City", "胡志明市", "Vietnam", "southeast_asia", False, ["ho chi minh", "phu my", "saigon"]),
    ("penang", "Penang", "檳城", "Malaysia", "southeast_asia", False, ["penang"]),
    ("port_klang", "Port Klang (Kuala Lumpur)", "巴生港（吉隆坡）", "Malaysia", "southeast_asia", False, ["port klang", "kuala lumpur"]),
    ("manila", "Manila", "馬尼拉", "Philippines", "southeast_asia", False, ["manila"]),
    ("bali", "Bali (Benoa)", "峇里島", "Indonesia", "southeast_asia", False, ["benoa", "bali"]),
    ("vancouver", "Vancouver", "溫哥華", "Canada", "alaska", False, ["vancouver"]),
    ("seattle", "Seattle", "西雅圖", "USA", "alaska", False, ["seattle"]),
    ("sydney", "Sydney", "雪梨", "Australia", "australia", False, ["sydney"]),
    ("honolulu", "Honolulu", "檀香山", "USA", "transpacific", False, ["honolulu"]),
]

# name, priority (⭐ 關注品牌), aliases
CRUISE_LINES = [
    ("MSC Cruises", True, ["msc"]),
    ("Disney Cruise Line", True, ["disney"]),
    ("Princess Cruises", True, ["princess"]),
    ("Star Cruises", True, ["star cruises", "麗星"]),
    ("Royal Caribbean", False, ["royal caribbean"]),
    ("Celebrity Cruises", False, ["celebrity"]),
    ("Holland America Line", False, ["holland america"]),
    ("Norwegian Cruise Line", False, ["norwegian", "ncl"]),
    ("Costa Cruises", False, ["costa"]),
    ("Carnival Cruise Line", False, ["carnival"]),
    ("Cunard", False, ["cunard"]),
    ("Oceania Cruises", False, ["oceania"]),
    ("Regent Seven Seas", False, ["regent"]),
    ("Silversea", False, ["silversea"]),
    ("Seabourn", False, ["seabourn"]),
    ("Viking", False, ["viking"]),
    ("Azamara", False, ["azamara"]),
    ("Windstar", False, ["windstar"]),
    ("Resorts World Cruises", False, ["resorts world"]),
]
