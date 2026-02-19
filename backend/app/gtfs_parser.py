import math
import os
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger("fluxroute.gtfs")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gtfs")

# Hardcoded TTC subway stations as fallback
TTC_SUBWAY_STATIONS = [
    # Line 1 Yonge-University (YU)
    {"stop_id": "YU_FINCH", "stop_name": "Finch", "stop_lat": 43.7804, "stop_lon": -79.4153, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_NYCTR", "stop_name": "North York Centre", "stop_lat": 43.7676, "stop_lon": -79.4131, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SHEPY", "stop_name": "Sheppard-Yonge", "stop_lat": 43.7615, "stop_lon": -79.4111, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_YORK", "stop_name": "York Mills", "stop_lat": 43.7440, "stop_lon": -79.4066, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_LAWR", "stop_name": "Lawrence", "stop_lat": 43.7251, "stop_lon": -79.4024, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_EGLN", "stop_name": "Eglinton", "stop_lat": 43.7057, "stop_lon": -79.3983, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_DAVS", "stop_name": "Davisville", "stop_lat": 43.6975, "stop_lon": -79.3971, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STCL", "stop_name": "St Clair", "stop_lat": 43.6880, "stop_lon": -79.3934, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SUMM", "stop_name": "Summerhill", "stop_lat": 43.6822, "stop_lon": -79.3910, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_ROSE", "stop_name": "Rosedale", "stop_lat": 43.6767, "stop_lon": -79.3887, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_BLRY", "stop_name": "Bloor-Yonge", "stop_lat": 43.6709, "stop_lon": -79.3857, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_WELL", "stop_name": "Wellesley", "stop_lat": 43.6655, "stop_lon": -79.3839, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_COLL", "stop_name": "College", "stop_lat": 43.6613, "stop_lon": -79.3827, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_DUND", "stop_name": "TMU", "stop_lat": 43.6559, "stop_lon": -79.3808, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_QUEN", "stop_name": "Queen", "stop_lat": 43.6523, "stop_lon": -79.3793, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_KING", "stop_name": "King", "stop_lat": 43.6490, "stop_lon": -79.3782, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_UNON", "stop_name": "Union", "stop_lat": 43.6453, "stop_lon": -79.3806, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STAN", "stop_name": "St Andrew", "stop_lat": 43.6476, "stop_lon": -79.3846, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_OSGO", "stop_name": "Osgoode", "stop_lat": 43.6507, "stop_lon": -79.3872, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STPA", "stop_name": "St Patrick", "stop_lat": 43.6548, "stop_lon": -79.3885, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_QNPK", "stop_name": "Queen's Park", "stop_lat": 43.6600, "stop_lon": -79.3909, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_MUSM", "stop_name": "Museum", "stop_lat": 43.6670, "stop_lon": -79.3935, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STGR", "stop_name": "St George", "stop_lat": 43.6683, "stop_lon": -79.3997, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SPAD", "stop_name": "Spadina", "stop_lat": 43.6672, "stop_lon": -79.4037, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_DUPO", "stop_name": "Dupont", "stop_lat": 43.6748, "stop_lon": -79.4069, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_STCW", "stop_name": "St Clair West", "stop_lat": 43.6841, "stop_lon": -79.4150, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_CDRV", "stop_name": "Cedarvale", "stop_lat": 43.6888, "stop_lon": -79.4224, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_GLNC", "stop_name": "Glencairn", "stop_lat": 43.7089, "stop_lon": -79.4412, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_LWST", "stop_name": "Lawrence West", "stop_lat": 43.7158, "stop_lon": -79.4440, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_YKDL", "stop_name": "Yorkdale", "stop_lat": 43.7245, "stop_lon": -79.4479, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_WLSN", "stop_name": "Wilson", "stop_lat": 43.7339, "stop_lon": -79.4502, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SHPW", "stop_name": "Sheppard West", "stop_lat": 43.7494, "stop_lon": -79.4618, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_DWPK", "stop_name": "Downsview Park", "stop_lat": 43.7535, "stop_lon": -79.4784, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_FNWT", "stop_name": "Finch West", "stop_lat": 43.7653, "stop_lon": -79.4910, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_YKUN", "stop_name": "York University", "stop_lat": 43.7735, "stop_lon": -79.5009, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_PNVL", "stop_name": "Pioneer Village", "stop_lat": 43.7778, "stop_lon": -79.5105, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_HW407", "stop_name": "Highway 407", "stop_lat": 43.7831, "stop_lon": -79.5231, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_VMC", "stop_name": "Vaughan Metropolitan Centre", "stop_lat": 43.7943, "stop_lon": -79.5273, "route_id": "1", "line": "Line 1 Yonge-University"},
    # Line 2 Bloor-Danforth (BD)
    {"stop_id": "BD_KPLG", "stop_name": "Kipling", "stop_lat": 43.6372, "stop_lon": -79.5361, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_ISLN", "stop_name": "Islington", "stop_lat": 43.6386, "stop_lon": -79.5246, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_RYLK", "stop_name": "Royal York", "stop_lat": 43.6482, "stop_lon": -79.5113, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_OLDM", "stop_name": "Old Mill", "stop_lat": 43.6502, "stop_lon": -79.4952, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_JANE", "stop_name": "Jane", "stop_lat": 43.6502, "stop_lon": -79.4838, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_RUNM", "stop_name": "Runnymede", "stop_lat": 43.6512, "stop_lon": -79.4754, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_HGPK", "stop_name": "High Park", "stop_lat": 43.6540, "stop_lon": -79.4668, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_KEEL", "stop_name": "Keele", "stop_lat": 43.6557, "stop_lon": -79.4597, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_DDWT", "stop_name": "Dundas West", "stop_lat": 43.6567, "stop_lon": -79.4526, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_LNSD", "stop_name": "Lansdowne", "stop_lat": 43.6595, "stop_lon": -79.4426, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_DFFR", "stop_name": "Dufferin", "stop_lat": 43.6601, "stop_lon": -79.4356, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_OSSN", "stop_name": "Ossington", "stop_lat": 43.6624, "stop_lon": -79.4267, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_CHRS", "stop_name": "Christie", "stop_lat": 43.6643, "stop_lon": -79.4185, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_BATH", "stop_name": "Bathurst", "stop_lat": 43.6660, "stop_lon": -79.4110, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_SPAD", "stop_name": "Spadina", "stop_lat": 43.6672, "stop_lon": -79.4037, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_STGR", "stop_name": "St George", "stop_lat": 43.6683, "stop_lon": -79.3997, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_BAY", "stop_name": "Bay", "stop_lat": 43.6700, "stop_lon": -79.3901, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_BLRY", "stop_name": "Bloor-Yonge", "stop_lat": 43.6709, "stop_lon": -79.3857, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_SHRB", "stop_name": "Sherbourne", "stop_lat": 43.6722, "stop_lon": -79.3764, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_CSTL", "stop_name": "Castle Frank", "stop_lat": 43.6741, "stop_lon": -79.3686, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_BRDV", "stop_name": "Broadview", "stop_lat": 43.6770, "stop_lon": -79.3584, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_CHST", "stop_name": "Chester", "stop_lat": 43.6783, "stop_lon": -79.3521, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_PAPE", "stop_name": "Pape", "stop_lat": 43.6799, "stop_lon": -79.3451, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_DNLD", "stop_name": "Donlands", "stop_lat": 43.6812, "stop_lon": -79.3375, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_GRWD", "stop_name": "Greenwood", "stop_lat": 43.6831, "stop_lon": -79.3302, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_CXWL", "stop_name": "Coxwell", "stop_lat": 43.6842, "stop_lon": -79.3228, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_WDBN", "stop_name": "Woodbine", "stop_lat": 43.6865, "stop_lon": -79.3126, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_MAIN", "stop_name": "Main Street", "stop_lat": 43.6890, "stop_lon": -79.3012, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_VCPK", "stop_name": "Victoria Park", "stop_lat": 43.6903, "stop_lon": -79.2930, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_WARD", "stop_name": "Warden", "stop_lat": 43.6917, "stop_lon": -79.2794, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_KNDY", "stop_name": "Kennedy", "stop_lat": 43.7326, "stop_lon": -79.2637, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    # Line 4 Sheppard
    {"stop_id": "SH_SHPY", "stop_name": "Sheppard-Yonge", "stop_lat": 43.7615, "stop_lon": -79.4111, "route_id": "4", "line": "Line 4 Sheppard"},
    {"stop_id": "SH_BAYV", "stop_name": "Bayview", "stop_lat": 43.7670, "stop_lon": -79.3868, "route_id": "4", "line": "Line 4 Sheppard"},
    {"stop_id": "SH_BESS", "stop_name": "Bessarion", "stop_lat": 43.7693, "stop_lon": -79.3763, "route_id": "4", "line": "Line 4 Sheppard"},
    {"stop_id": "SH_LESL", "stop_name": "Leslie", "stop_lat": 43.7710, "stop_lon": -79.3659, "route_id": "4", "line": "Line 4 Sheppard"},
    {"stop_id": "SH_DNML", "stop_name": "Don Mills", "stop_lat": 43.7757, "stop_lon": -79.3461, "route_id": "4", "line": "Line 4 Sheppard"},
    # Line 5 Eglinton Crosstown LRT (25 stations: Mount Dennis → Kennedy)
    {"stop_id": "EC_MTDN", "stop_name": "Mount Dennis", "stop_lat": 43.6880, "stop_lon": -79.4858, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_KEEL", "stop_name": "Keelesdale", "stop_lat": 43.6904, "stop_lon": -79.4745, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_CRST", "stop_name": "Caledonia", "stop_lat": 43.6923, "stop_lon": -79.4651, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_FAIR", "stop_name": "Fairbank", "stop_lat": 43.6957, "stop_lon": -79.4493, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_OAKW", "stop_name": "Oakwood", "stop_lat": 43.6975, "stop_lon": -79.4427, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_CDVL", "stop_name": "Cedarvale", "stop_lat": 43.6989, "stop_lon": -79.4356, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_FHLS", "stop_name": "Forest Hill", "stop_lat": 43.7012, "stop_lon": -79.4251, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_CHPL", "stop_name": "Chaplin", "stop_lat": 43.7030, "stop_lon": -79.4171, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_AVEN", "stop_name": "Avenue", "stop_lat": 43.7047, "stop_lon": -79.4087, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_EGLN", "stop_name": "Eglinton", "stop_lat": 43.7064, "stop_lon": -79.3988, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_MTPL", "stop_name": "Mount Pleasant", "stop_lat": 43.7085, "stop_lon": -79.3903, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_LIRD", "stop_name": "Leaside", "stop_lat": 43.7108, "stop_lon": -79.3765, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_LAER", "stop_name": "Laird", "stop_lat": 43.7132, "stop_lon": -79.3647, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_SNBK", "stop_name": "Sunnybrook Park", "stop_lat": 43.7174, "stop_lon": -79.3487, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_DNVL", "stop_name": "Don Valley", "stop_lat": 43.7200, "stop_lon": -79.3389, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_AMES", "stop_name": "Aga Khan Park & Museum", "stop_lat": 43.7225, "stop_lon": -79.3323, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_WYNF", "stop_name": "Wynford", "stop_lat": 43.7241, "stop_lon": -79.3262, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_SLVR", "stop_name": "Sloane", "stop_lat": 43.7258, "stop_lon": -79.3123, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_ODNN", "stop_name": "O'Connor", "stop_lat": 43.7248, "stop_lon": -79.3013, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_PHRM", "stop_name": "Pharmacy", "stop_lat": 43.7259, "stop_lon": -79.2963, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_HKME", "stop_name": "Hakimi Lebovic", "stop_lat": 43.7272, "stop_lon": -79.2903, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_GLDM", "stop_name": "Golden Mile", "stop_lat": 43.7281, "stop_lon": -79.2864, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_BRCH", "stop_name": "Birchmount", "stop_lat": 43.7302, "stop_lon": -79.2766, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_IONV", "stop_name": "Ionview", "stop_lat": 43.7314, "stop_lon": -79.2717, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_KNDY", "stop_name": "Kennedy", "stop_lat": 43.7328, "stop_lon": -79.2645, "route_id": "5", "line": "Line 5 Eglinton"},
    # Line 6 Finch West LRT (18 stations: Finch West → Humber College)
    {"stop_id": "FW_FNCH", "stop_name": "Finch West", "stop_lat": 43.7631, "stop_lon": -79.4907, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_SNTN", "stop_name": "Sentinel", "stop_lat": 43.7611, "stop_lon": -79.4998, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_TOBR", "stop_name": "Tobermory", "stop_lat": 43.7593, "stop_lon": -79.5077, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_DRFT", "stop_name": "Driftwood", "stop_lat": 43.7581, "stop_lon": -79.5132, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_JANE", "stop_name": "Jane and Finch", "stop_lat": 43.7572, "stop_lon": -79.5174, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_NRFN", "stop_name": "Norfinch Oakdale", "stop_lat": 43.7560, "stop_lon": -79.5240, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_SGWY", "stop_name": "Signet Arrow", "stop_lat": 43.7533, "stop_lon": -79.5360, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_EMRY", "stop_name": "Emery", "stop_lat": 43.7521, "stop_lon": -79.5421, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_MLVN", "stop_name": "Milvan Rumike", "stop_lat": 43.7500, "stop_lon": -79.5520, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_DNCN", "stop_name": "Duncanwoods", "stop_lat": 43.7488, "stop_lon": -79.5573, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_PRKS", "stop_name": "Pearldale", "stop_lat": 43.7477, "stop_lon": -79.5625, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_RNTM", "stop_name": "Rowntree Mills", "stop_lat": 43.7464, "stop_lon": -79.5683, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_MTOL", "stop_name": "Mount Olive", "stop_lat": 43.7433, "stop_lon": -79.5818, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_STVN", "stop_name": "Stevenson", "stop_lat": 43.7432, "stop_lon": -79.5870, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_ALBW", "stop_name": "Albion", "stop_lat": 43.7414, "stop_lon": -79.5890, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_MTNR", "stop_name": "Martin Grove", "stop_lat": 43.7367, "stop_lon": -79.5919, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_WSTM", "stop_name": "Westmore", "stop_lat": 43.7348, "stop_lon": -79.6007, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_HMBR", "stop_name": "Humber College", "stop_lat": 43.7299, "stop_lon": -79.6014, "route_id": "6", "line": "Line 6 Finch West"},
]

# Hardcoded GO Transit rail lines as fallback when OTP is unavailable.
# Coordinates are [lng, lat] (GeoJSON convention).
GO_TRANSIT_LINES: dict = {
    "lines": [
        {
            "type": "Feature",
            "properties": {
                "id": "go:LSW",
                "shortName": "LSW",
                "longName": "Lakeshore West",
                "mode": "RAIL",
                "color": "#3D8B37",
                "agencyName": "GO Transit",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-79.8711, 43.2557],  # Hamilton GO Centre
                    [-79.8337, 43.3147],  # Aldershot
                    [-79.7972, 43.3313],  # Burlington
                    [-79.7655, 43.3631],  # Appleby
                    [-79.7249, 43.3997],  # Bronte
                    [-79.6810, 43.4470],  # Oakville
                    [-79.6376, 43.5073],  # Clarkson
                    [-79.5871, 43.5461],  # Port Credit
                    [-79.5466, 43.5856],  # Long Branch
                    [-79.5073, 43.6077],  # Mimico
                    [-79.4214, 43.6354],  # Exhibition
                    [-79.3806, 43.6453],  # Union
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "id": "go:LSE",
                "shortName": "LSE",
                "longName": "Lakeshore East",
                "mode": "RAIL",
                "color": "#3D8B37",
                "agencyName": "GO Transit",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-78.8437, 43.9001],  # Oshawa
                    [-78.9411, 43.8726],  # Whitby
                    [-79.0298, 43.8466],  # Ajax
                    [-79.0863, 43.8321],  # Pickering
                    [-79.1303, 43.7891],  # Rouge Hill
                    [-79.1760, 43.7555],  # Guildwood
                    [-79.2217, 43.7271],  # Scarborough
                    [-79.3102, 43.6858],  # Danforth
                    [-79.3806, 43.6453],  # Union
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "id": "go:KIT",
                "shortName": "KIT",
                "longName": "Kitchener",
                "mode": "RAIL",
                "color": "#3D8B37",
                "agencyName": "GO Transit",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-80.4985, 43.4525],  # Kitchener
                    [-80.2494, 43.5455],  # Guelph
                    [-79.9215, 43.6478],  # Georgetown
                    [-79.8178, 43.6690],  # Mount Pleasant
                    [-79.7678, 43.6842],  # Brampton
                    [-79.7283, 43.7064],  # Bramalea
                    [-79.6578, 43.7094],  # Malton
                    [-79.5814, 43.7264],  # Etobicoke North
                    [-79.5212, 43.7061],  # Weston
                    [-79.4542, 43.6641],  # Bloor
                    [-79.3806, 43.6453],  # Union
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "id": "go:BAR",
                "shortName": "BAR",
                "longName": "Barrie",
                "mode": "RAIL",
                "color": "#3D8B37",
                "agencyName": "GO Transit",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-79.6892, 44.3785],  # Barrie South
                    [-79.5640, 44.1135],  # Bradford
                    [-79.4773, 44.0571],  # Newmarket
                    [-79.4557, 44.0030],  # Aurora
                    [-79.5297, 43.9205],  # King City
                    [-79.5102, 43.8507],  # Maple
                    [-79.5247, 43.8317],  # Rutherford
                    [-79.4264, 43.8140],  # Langstaff
                    [-79.4076, 43.7758],  # Oriole
                    [-79.4032, 43.7601],  # Old Cummer
                    [-79.4781, 43.7536],  # Downsview Park
                    [-79.4542, 43.6641],  # Bloor
                    [-79.3806, 43.6453],  # Union
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "id": "go:STO",
                "shortName": "STO",
                "longName": "Stouffville",
                "mode": "RAIL",
                "color": "#3D8B37",
                "agencyName": "GO Transit",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-79.2575, 44.0327],  # Lincolnville
                    [-79.2558, 43.9715],  # Stouffville
                    [-79.2599, 43.8879],  # Mount Joy
                    [-79.2636, 43.8589],  # Markham
                    [-79.2890, 43.8361],  # Unionville
                    [-79.2892, 43.8096],  # Centennial
                    [-79.2844, 43.7810],  # Agincourt
                    [-79.2635, 43.7344],  # Kennedy
                    [-79.3102, 43.6858],  # Danforth
                    [-79.3806, 43.6453],  # Union
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "id": "go:RH",
                "shortName": "RH",
                "longName": "Richmond Hill",
                "mode": "RAIL",
                "color": "#3D8B37",
                "agencyName": "GO Transit",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-79.3660, 44.0421],  # Gormley
                    [-79.3614, 43.9501],  # Richmond Hill
                    [-79.4264, 43.8140],  # Langstaff
                    [-79.4032, 43.7601],  # Old Cummer
                    [-79.4076, 43.7758],  # Oriole
                    [-79.4542, 43.6641],  # Bloor
                    [-79.3806, 43.6453],  # Union
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "id": "go:MIL",
                "shortName": "MIL",
                "longName": "Milton",
                "mode": "RAIL",
                "color": "#3D8B37",
                "agencyName": "GO Transit",
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-79.8817, 43.5177],  # Milton
                    [-79.8005, 43.5785],  # Lisgar
                    [-79.7686, 43.5884],  # Meadowvale
                    [-79.7202, 43.5917],  # Streetsville
                    [-79.6760, 43.5903],  # Erindale
                    [-79.6254, 43.5902],  # Cooksville
                    [-79.5871, 43.5461],  # Port Credit
                    [-79.5466, 43.5856],  # Long Branch
                    [-79.5073, 43.6077],  # Mimico
                    [-79.3806, 43.6453],  # Union
                ],
            },
        },
    ],
    "stations": [
        # Lakeshore West key stops
        {"type": "Feature", "properties": {"name": "Hamilton GO Centre", "stopId": "go:HAM", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSW"}, "geometry": {"type": "Point", "coordinates": [-79.8711, 43.2557]}},
        {"type": "Feature", "properties": {"name": "Aldershot", "stopId": "go:ALD", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSW"}, "geometry": {"type": "Point", "coordinates": [-79.8337, 43.3147]}},
        {"type": "Feature", "properties": {"name": "Burlington", "stopId": "go:BUR", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSW"}, "geometry": {"type": "Point", "coordinates": [-79.7972, 43.3313]}},
        {"type": "Feature", "properties": {"name": "Oakville", "stopId": "go:OAK", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSW"}, "geometry": {"type": "Point", "coordinates": [-79.6810, 43.4470]}},
        {"type": "Feature", "properties": {"name": "Port Credit", "stopId": "go:PTC", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSW"}, "geometry": {"type": "Point", "coordinates": [-79.5871, 43.5461]}},
        {"type": "Feature", "properties": {"name": "Mimico", "stopId": "go:MIM", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSW"}, "geometry": {"type": "Point", "coordinates": [-79.5073, 43.6077]}},
        # Lakeshore East key stops
        {"type": "Feature", "properties": {"name": "Oshawa", "stopId": "go:OSH", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSE"}, "geometry": {"type": "Point", "coordinates": [-78.8437, 43.9001]}},
        {"type": "Feature", "properties": {"name": "Whitby", "stopId": "go:WHI", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSE"}, "geometry": {"type": "Point", "coordinates": [-78.9411, 43.8726]}},
        {"type": "Feature", "properties": {"name": "Ajax", "stopId": "go:AJX", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSE"}, "geometry": {"type": "Point", "coordinates": [-79.0298, 43.8466]}},
        {"type": "Feature", "properties": {"name": "Pickering", "stopId": "go:PIK", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSE"}, "geometry": {"type": "Point", "coordinates": [-79.0863, 43.8321]}},
        {"type": "Feature", "properties": {"name": "Scarborough GO", "stopId": "go:SCA", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "LSE"}, "geometry": {"type": "Point", "coordinates": [-79.2217, 43.7271]}},
        # Kitchener key stops
        {"type": "Feature", "properties": {"name": "Kitchener", "stopId": "go:KIT", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "KIT"}, "geometry": {"type": "Point", "coordinates": [-80.4985, 43.4525]}},
        {"type": "Feature", "properties": {"name": "Guelph Central", "stopId": "go:GUE", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "KIT"}, "geometry": {"type": "Point", "coordinates": [-80.2494, 43.5455]}},
        {"type": "Feature", "properties": {"name": "Georgetown", "stopId": "go:GEO", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "KIT"}, "geometry": {"type": "Point", "coordinates": [-79.9215, 43.6478]}},
        {"type": "Feature", "properties": {"name": "Brampton", "stopId": "go:BRA", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "KIT"}, "geometry": {"type": "Point", "coordinates": [-79.7678, 43.6842]}},
        {"type": "Feature", "properties": {"name": "Weston", "stopId": "go:WES", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "KIT"}, "geometry": {"type": "Point", "coordinates": [-79.5212, 43.7061]}},
        # Barrie key stops
        {"type": "Feature", "properties": {"name": "Barrie South", "stopId": "go:BRS", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "BAR"}, "geometry": {"type": "Point", "coordinates": [-79.6892, 44.3785]}},
        {"type": "Feature", "properties": {"name": "Newmarket", "stopId": "go:NEW", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "BAR"}, "geometry": {"type": "Point", "coordinates": [-79.4773, 44.0571]}},
        {"type": "Feature", "properties": {"name": "Aurora", "stopId": "go:AUR", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "BAR"}, "geometry": {"type": "Point", "coordinates": [-79.4557, 44.0030]}},
        {"type": "Feature", "properties": {"name": "King City", "stopId": "go:KGC", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "BAR"}, "geometry": {"type": "Point", "coordinates": [-79.5297, 43.9205]}},
        {"type": "Feature", "properties": {"name": "Maple", "stopId": "go:MAP", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "BAR"}, "geometry": {"type": "Point", "coordinates": [-79.5102, 43.8507]}},
        # Stouffville key stops
        {"type": "Feature", "properties": {"name": "Lincolnville", "stopId": "go:LIN", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "STO"}, "geometry": {"type": "Point", "coordinates": [-79.2575, 44.0327]}},
        {"type": "Feature", "properties": {"name": "Stouffville", "stopId": "go:STV", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "STO"}, "geometry": {"type": "Point", "coordinates": [-79.2558, 43.9715]}},
        {"type": "Feature", "properties": {"name": "Markham", "stopId": "go:MRK", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "STO"}, "geometry": {"type": "Point", "coordinates": [-79.2636, 43.8589]}},
        {"type": "Feature", "properties": {"name": "Unionville", "stopId": "go:UNV", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "STO"}, "geometry": {"type": "Point", "coordinates": [-79.2890, 43.8361]}},
        # Richmond Hill key stops
        {"type": "Feature", "properties": {"name": "Gormley", "stopId": "go:GOR", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "RH"}, "geometry": {"type": "Point", "coordinates": [-79.3660, 44.0421]}},
        {"type": "Feature", "properties": {"name": "Richmond Hill", "stopId": "go:RHL", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "RH"}, "geometry": {"type": "Point", "coordinates": [-79.3614, 43.9501]}},
        # Milton key stops
        {"type": "Feature", "properties": {"name": "Milton", "stopId": "go:MLT", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "MIL"}, "geometry": {"type": "Point", "coordinates": [-79.8817, 43.5177]}},
        {"type": "Feature", "properties": {"name": "Mississauga", "stopId": "go:MSS", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "MIL"}, "geometry": {"type": "Point", "coordinates": [-79.6254, 43.5902]}},
        # Shared terminal
        {"type": "Feature", "properties": {"name": "Union Station", "stopId": "go:UNI", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "GO Transit"}, "geometry": {"type": "Point", "coordinates": [-79.3806, 43.6453]}},
        {"type": "Feature", "properties": {"name": "Bloor GO", "stopId": "go:BLR", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "GO Transit"}, "geometry": {"type": "Point", "coordinates": [-79.4542, 43.6641]}},
        {"type": "Feature", "properties": {"name": "Danforth GO", "stopId": "go:DAN", "mode": "RAIL", "color": "#3D8B37", "agencyName": "GO Transit", "routeName": "GO Transit"}, "geometry": {"type": "Point", "coordinates": [-79.3102, 43.6858]}},
    ],
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_gtfs_data() -> dict:
    """Load GTFS static data from files, falling back to hardcoded stations."""
    data = {"stops": pd.DataFrame(), "routes": pd.DataFrame(), "shapes": pd.DataFrame(),
            "trips": pd.DataFrame(), "stop_times": pd.DataFrame(),
            "calendar": pd.DataFrame(), "calendar_dates": pd.DataFrame(),
            "using_fallback": False}

    files = {
        "stops": "stops.txt",
        "routes": "routes.txt",
        "shapes": "shapes.txt",
        "trips": "trips.txt",
        "stop_times": "stop_times.txt",
        "calendar": "calendar.txt",
        "calendar_dates": "calendar_dates.txt",
    }

    columns_map = {
        "stops": ["stop_id", "stop_name", "stop_lat", "stop_lon", "route_id", "line"],
        "stop_times": ["trip_id", "stop_id", "arrival_time", "departure_time", "stop_sequence"],
        "trips": ["route_id", "service_id", "trip_id", "trip_headsign", "shape_id"],
        "shapes": ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
        "routes": ["route_id", "route_short_name", "route_long_name", "route_color", "route_type"],
        "calendar": ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"],
        "calendar_dates": ["service_id", "date", "exception_type"],
    }

    try:
        for key, fname in files.items():
            fpath = os.path.join(DATA_DIR, fname)
            if os.path.exists(fpath):
                # Only load columns that exist in the file to avoid errors
                usecols = None
                if key in columns_map:
                    # quick check of header
                    with open(fpath, 'r', encoding='utf-8-sig') as f:
                        header = f.readline().strip().split(',')
                    usecols = [c for c in columns_map[key] if c in header]

                data[key] = pd.read_csv(fpath, usecols=usecols, low_memory=False)
                logger.info(f"Loaded {key}: {len(data[key])} rows")
            else:
                logger.warning(f"GTFS file not found: {fpath}")
    except Exception as e:
        logger.error(f"Error loading GTFS files: {e}")

    # If stops are empty, use fallback
    if data["stops"].empty:
        logger.warning("Using hardcoded TTC subway station fallback")
        data["stops"] = pd.DataFrame(TTC_SUBWAY_STATIONS)
        data["using_fallback"] = True

    # Pre-convert stop_id to string for fast lookups (avoids .astype(str) on 4M rows)
    if not data["stop_times"].empty and "stop_id" in data["stop_times"].columns:
        data["stop_times"]["stop_id"] = data["stop_times"]["stop_id"].astype(str)
    if not data["stops"].empty and "stop_id" in data["stops"].columns:
        data["stops"]["stop_id"] = data["stops"]["stop_id"].astype(str)

    # Build rapid transit index: stop_id → {route_id, route_short_name, route_long_name, route_type}
    # This avoids scanning 4.2M stop_times rows per stop during route lookups
    rapid_index: dict[str, dict] = {}
    routes_df = data.get("routes", pd.DataFrame())
    trips_df = data.get("trips", pd.DataFrame())
    stop_times_df = data.get("stop_times", pd.DataFrame())
    if not routes_df.empty and "route_type" in routes_df.columns and not trips_df.empty and not stop_times_df.empty:
        rapid_types = {0, 1, 2}
        rapid_routes = routes_df[routes_df["route_type"].isin(rapid_types)]
        if not rapid_routes.empty:
            rapid_route_ids = set(rapid_routes["route_id"].unique())
            rapid_trips = trips_df[trips_df["route_id"].isin(rapid_route_ids)]
            # Build trip_id → route_id map
            trip_to_route = dict(zip(rapid_trips["trip_id"], rapid_trips["route_id"]))
            # Build route_id → route info map
            route_info_map = {}
            for _, r in rapid_routes.iterrows():
                rid = r["route_id"]
                route_info_map[rid] = {
                    "route_id": rid,
                    "route_short_name": str(r.get("route_short_name", "")) if pd.notna(r.get("route_short_name")) else "",
                    "route_long_name": str(r.get("route_long_name", "")) if pd.notna(r.get("route_long_name")) else "",
                }
            # Scan stop_times once to map stop_id → route info
            rapid_trip_ids = set(trip_to_route.keys())
            rapid_st = stop_times_df[stop_times_df["trip_id"].isin(rapid_trip_ids)]
            for stop_id, trip_id in zip(rapid_st["stop_id"].values, rapid_st["trip_id"].values):
                if stop_id not in rapid_index:
                    route_id = trip_to_route.get(trip_id)
                    if route_id and route_id in route_info_map:
                        rapid_index[stop_id] = route_info_map[route_id]
            logger.info(f"Built rapid transit index: {len(rapid_index)} stops")
    data["_rapid_index"] = rapid_index

    return data


def find_nearest_rapid_transit_stations(
    gtfs: dict, lat: float, lng: float, radius_km: float = 15.0, limit: int = 10
) -> list[dict]:
    """Find nearest subway/rail/LRT stations (NOT bus stops).

    Filters to route_type 0 (Tram/LRT), 1 (Subway), 2 (Rail).
    If using fallback data, uses TTC_SUBWAY_STATIONS directly.
    """
    stops = gtfs["stops"]
    routes_df = gtfs.get("routes", pd.DataFrame())
    trips_df = gtfs.get("trips", pd.DataFrame())
    stop_times_df = gtfs.get("stop_times", pd.DataFrame())

    if gtfs.get("using_fallback") or routes_df.empty or "route_type" not in routes_df.columns:
        # Fallback: TTC_SUBWAY_STATIONS are already filtered
        results = []
        for s in TTC_SUBWAY_STATIONS:
            dist = haversine(lat, lng, s["stop_lat"], s["stop_lon"])
            if dist <= radius_km:
                results.append({
                    "stop_id": s["stop_id"],
                    "stop_name": s["stop_name"],
                    "lat": s["stop_lat"],
                    "lng": s["stop_lon"],
                    "distance_km": round(dist, 3),
                    "route_id": s.get("route_id"),
                    "line": s.get("line"),
                })
        results.sort(key=lambda x: x["distance_km"])
        return results[:limit]

    # Use prebuilt rapid transit index for O(1) lookups
    rapid_index = gtfs.get("_rapid_index", {})
    if not rapid_index:
        return []

    rapid_stop_ids = set(rapid_index.keys())
    rapid_stops = stops[stops["stop_id"].isin(rapid_stop_ids)]

    if rapid_stops.empty:
        return []

    # Compute distances
    lat_col = "stop_lat" if "stop_lat" in rapid_stops.columns else "latitude"
    lng_col = "stop_lon" if "stop_lon" in rapid_stops.columns else "longitude"

    results = []
    for _, row in rapid_stops.iterrows():
        s_lat = float(row[lat_col])
        s_lng = float(row[lng_col])
        dist = haversine(lat, lng, s_lat, s_lng)
        if dist <= radius_km:
            stop_id = str(row["stop_id"])
            info = rapid_index.get(stop_id, {})
            route_id = info.get("route_id")
            sn = info.get("route_short_name", "")
            ln = info.get("route_long_name", "")
            if ln.lower().startswith("line"):
                line = ln
            elif sn:
                line = f"Line {sn} {ln}".strip()
            else:
                line = ln or None

            results.append({
                "stop_id": str(stop_id),
                "stop_name": str(row.get("stop_name", "Unknown")),
                "lat": s_lat,
                "lng": s_lng,
                "distance_km": round(dist, 3),
                "route_id": str(route_id) if route_id is not None else None,
                "line": line,
            })

    # Deduplicate by base station name (keep closest)
    # Strip platform suffixes like " - Subway Platform", " - Southbound Platform"
    def _base_name(name: str) -> str:
        for sep in [" - ", " Station"]:
            if sep in name:
                name = name.split(sep)[0]
        return name.strip()

    seen_names = {}
    deduped = []
    for r in sorted(results, key=lambda x: x["distance_km"]):
        base = _base_name(r["stop_name"])
        if base not in seen_names:
            seen_names[base] = True
            # Clean up the display name too
            r["stop_name"] = base
            deduped.append(r)

    return deduped[:limit]


def find_nearest_stops(gtfs: dict, lat: float, lng: float, radius_km: float = 2.0, limit: int = 5) -> list[dict]:
    """Find nearest stops using vectorized distance calculation."""
    stops = gtfs["stops"]
    if stops.empty:
        return []

    lat_col = "stop_lat" if "stop_lat" in stops.columns else "latitude"
    lng_col = "stop_lon" if "stop_lon" in stops.columns else "longitude"

    # Vectorized haversine
    lat_r = math.radians(lat)
    stops_lat_r = stops[lat_col].apply(math.radians)
    stops_lng_r = stops[lng_col].apply(math.radians)
    lng_r = math.radians(lng)

    dlat = stops_lat_r - lat_r
    dlng = stops_lng_r - lng_r

    a = (dlat / 2).apply(math.sin) ** 2 + math.cos(lat_r) * stops_lat_r.apply(math.cos) * (dlng / 2).apply(math.sin) ** 2
    a = a.clip(upper=1.0)  # Clamp to prevent math domain error from float precision
    distances = 6371.0 * 2 * (a.apply(math.sqrt).apply(lambda x: math.atan2(x, math.sqrt(1 - x))))

    stops_with_dist = stops.copy()
    stops_with_dist["distance_km"] = distances

    nearby = stops_with_dist[stops_with_dist["distance_km"] <= radius_km].nsmallest(limit, "distance_km")

    # Use rapid transit index for fast route enrichment
    rapid_index = gtfs.get("_rapid_index", {})

    results = []
    for _, row in nearby.iterrows():
        stop_id = str(row.get("stop_id", ""))
        stop_name = row.get("stop_name", "Unknown")
        route_id = row.get("route_id", None)
        line = row.get("line", None)

        # Enrich with route info from prebuilt index
        if (route_id is None or line is None) and stop_id in rapid_index:
            info = rapid_index[stop_id]
            if route_id is None:
                route_id = info.get("route_id")
            if line is None:
                sn = info.get("route_short_name", "")
                ln = info.get("route_long_name", "")
                if ln.lower().startswith("line"):
                    line = ln
                elif sn:
                    line = f"{sn} {ln}".strip()
                else:
                    line = ln or None

        results.append({
            "stop_id": str(stop_id),
            "stop_name": stop_name,
            "lat": row[lat_col],
            "lng": row[lng_col],
            "distance_km": round(row["distance_km"], 3),
            "route_id": str(route_id) if route_id is not None else None,
            "line": line,
        })

    return results


def search_stops(gtfs: dict, query: str, limit: int = 5) -> list[dict]:
    """Search GTFS stops by name (case-insensitive partial match).

    Starts-with matches are ranked before contains matches.
    Deduplicates by base station name (strips platform suffixes).
    Works with both full GTFS DataFrame and TTC_SUBWAY_STATIONS fallback.
    """
    if not query or len(query) < 2:
        return []

    query_lower = query.lower()

    def _base_name(name: str) -> str:
        for sep in [" - ", " Station"]:
            if sep in name:
                name = name.split(sep)[0]
        return name.strip()

    stops = gtfs.get("stops", pd.DataFrame())

    # Build candidate list from either DataFrame or fallback
    candidates: list[dict] = []
    if gtfs.get("using_fallback") or stops.empty:
        for s in TTC_SUBWAY_STATIONS:
            candidates.append({
                "stop_id": s["stop_id"],
                "stop_name": s["stop_name"],
                "lat": s["stop_lat"],
                "lng": s["stop_lon"],
                "route_id": s.get("route_id"),
                "line": s.get("line"),
            })
    else:
        lat_col = "stop_lat" if "stop_lat" in stops.columns else "latitude"
        lng_col = "stop_lon" if "stop_lon" in stops.columns else "longitude"
        for _, row in stops.iterrows():
            candidates.append({
                "stop_id": str(row.get("stop_id", "")),
                "stop_name": str(row.get("stop_name", "")),
                "lat": float(row[lat_col]),
                "lng": float(row[lng_col]),
                "route_id": str(row["route_id"]) if "route_id" in row and pd.notna(row.get("route_id")) else None,
                "line": str(row["line"]) if "line" in row and pd.notna(row.get("line")) else None,
            })

    # Match: starts-with first, then contains
    starts_with: list[dict] = []
    contains: list[dict] = []
    for c in candidates:
        base = _base_name(c["stop_name"])
        base_lower = base.lower()
        if base_lower.startswith(query_lower):
            c["stop_name"] = base
            starts_with.append(c)
        elif query_lower in base_lower:
            c["stop_name"] = base
            contains.append(c)

    merged = starts_with + contains

    # Deduplicate by base name (keep first occurrence)
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in merged:
        key = item["stop_name"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:limit]


def get_route_shape_segment(
    gtfs: dict, route_id: str,
    board_lat: float, board_lng: float,
    alight_lat: float, alight_lng: float,
) -> Optional[dict]:
    """Get the GTFS shape clipped between board and alight stop coordinates.

    Returns a GeoJSON LineString following the actual track between two stops,
    or None if shapes data is unavailable.
    """
    shapes = gtfs.get("shapes", pd.DataFrame())
    trips = gtfs.get("trips", pd.DataFrame())

    if shapes.empty or trips.empty:
        return None

    route_trips = trips[trips["route_id"].astype(str) == str(route_id)]
    if route_trips.empty:
        return None

    shape_id = route_trips.iloc[0].get("shape_id")
    if pd.isna(shape_id):
        return None

    shape_points = shapes[shapes["shape_id"] == shape_id].sort_values("shape_pt_sequence")
    if shape_points.empty:
        return None

    coords = list(zip(shape_points["shape_pt_lon"].values, shape_points["shape_pt_lat"].values))

    # Find nearest shape point to board and alight stops
    def nearest_idx(lat: float, lng: float) -> int:
        best_i, best_d = 0, float("inf")
        for i, (lon, la) in enumerate(coords):
            d = (la - lat) ** 2 + (lon - lng) ** 2
            if d < best_d:
                best_d = d
                best_i = i
        return best_i

    board_idx = nearest_idx(board_lat, board_lng)
    alight_idx = nearest_idx(alight_lat, alight_lng)

    if board_idx == alight_idx:
        return None

    lo, hi = min(board_idx, alight_idx), max(board_idx, alight_idx)
    segment = coords[lo:hi + 1]

    # If board comes after alight in the shape, reverse
    if board_idx > alight_idx:
        segment = list(reversed(segment))

    if len(segment) < 2:
        return None

    return {"type": "LineString", "coordinates": [[lon, lat] for lon, lat in segment]}


def get_route_shape(gtfs: dict, route_id: str) -> Optional[dict]:
    """Get GeoJSON LineString for a route from shapes.txt."""
    shapes = gtfs.get("shapes", pd.DataFrame())
    trips = gtfs.get("trips", pd.DataFrame())

    if shapes.empty or trips.empty:
        return _get_fallback_shape(gtfs, route_id)

    # Find a shape_id for this route
    route_trips = trips[trips["route_id"].astype(str) == str(route_id)]
    if route_trips.empty:
        return _get_fallback_shape(gtfs, route_id)

    shape_id = route_trips.iloc[0].get("shape_id")
    if pd.isna(shape_id):
        return _get_fallback_shape(gtfs, route_id)

    shape_points = shapes[shapes["shape_id"] == shape_id].sort_values("shape_pt_sequence")
    if shape_points.empty:
        return _get_fallback_shape(gtfs, route_id)

    coordinates = [[row["shape_pt_lon"], row["shape_pt_lat"]] for _, row in shape_points.iterrows()]

    return {"type": "LineString", "coordinates": coordinates}


def _get_fallback_shape(gtfs: dict, route_id: str) -> Optional[dict]:
    """Generate shape from station coordinates for fallback data."""
    stops = gtfs["stops"]
    if "route_id" not in stops.columns:
        return None

    route_stops = stops[stops["route_id"].astype(str) == str(route_id)]
    if route_stops.empty:
        return None

    lat_col = "stop_lat" if "stop_lat" in stops.columns else "latitude"
    lng_col = "stop_lon" if "stop_lon" in stops.columns else "longitude"

    coordinates = [[row[lng_col], row[lat_col]] for _, row in route_stops.iterrows()]
    return {"type": "LineString", "coordinates": coordinates}


def _parse_gtfs_time(t: str) -> int:
    """Parse GTFS time like '25:30:00' to minutes since midnight."""
    try:
        parts = str(t).split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return 0


def _format_gtfs_time(minutes: int) -> str:
    """Format minutes since midnight to HH:MM (normalizing 25:00+ to 01:00+)."""
    h, m = divmod(minutes % 1440, 60)
    return f"{h:02d}:{m:02d}"


def get_active_service_ids(gtfs: dict, date: Optional[datetime] = None) -> set:
    """Get service IDs active on the given date (or today).

    Uses calendar.txt (day-of-week + date range) and calendar_dates.txt (exceptions).
    Falls back to returning all service_ids from trips if no calendar data.
    """
    if date is None:
        date = datetime.now()

    calendar = gtfs.get("calendar", pd.DataFrame())
    calendar_dates = gtfs.get("calendar_dates", pd.DataFrame())
    trips = gtfs.get("trips", pd.DataFrame())

    if calendar.empty:
        # Permissive fallback: return all service_ids from trips
        if not trips.empty and "service_id" in trips.columns:
            return set(trips["service_id"].unique())
        return set()

    # Day-of-week column names
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today_day = day_names[date.weekday()]
    today_int = int(date.strftime("%Y%m%d"))

    active = set()
    for _, row in calendar.iterrows():
        try:
            start = int(row.get("start_date", 0))
            end = int(row.get("end_date", 99999999))
            if start <= today_int <= end and int(row.get(today_day, 0)) == 1:
                active.add(row["service_id"])
        except (ValueError, TypeError):
            continue

    # Apply calendar_dates exceptions
    if not calendar_dates.empty and "date" in calendar_dates.columns:
        for _, row in calendar_dates.iterrows():
            try:
                exc_date = int(row["date"])
                if exc_date != today_int:
                    continue
                exc_type = int(row.get("exception_type", 0))
                sid = row["service_id"]
                if exc_type == 1:
                    active.add(sid)
                elif exc_type == 2:
                    active.discard(sid)
            except (ValueError, TypeError):
                continue

    # If calendar data exists but nothing matched, fall back to all service_ids
    if not active and not trips.empty and "service_id" in trips.columns:
        return set(trips["service_id"].unique())

    return active


def get_next_departures(
    gtfs: dict, stop_id: str, limit: int = 5,
    route_id: Optional[str] = None, service_ids: Optional[set] = None,
) -> list[dict]:
    """Get next departures from a stop, handling GTFS 25:00:00 time format.

    Optionally filter by route_id and active service_ids for more accurate results.
    """
    stop_times = gtfs.get("stop_times", pd.DataFrame())
    if stop_times.empty:
        return _generate_mock_departures(stop_id, limit)

    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    stop_deps = stop_times[stop_times["stop_id"] == str(stop_id)].copy()
    if stop_deps.empty:
        return _generate_mock_departures(stop_id, limit)

    # Filter by service_ids (active services for today)
    trips_df = gtfs.get("trips", pd.DataFrame())
    if service_ids and not trips_df.empty and "service_id" in trips_df.columns:
        active_trips = trips_df[trips_df["service_id"].isin(service_ids)]
        if route_id is not None:
            active_trips = active_trips[active_trips["route_id"].astype(str) == str(route_id)]
        active_trip_ids = set(active_trips["trip_id"])
        if active_trip_ids:
            stop_deps = stop_deps[stop_deps["trip_id"].isin(active_trip_ids)]
    elif route_id is not None and not trips_df.empty:
        route_trips = trips_df[trips_df["route_id"].astype(str) == str(route_id)]
        route_trip_ids = set(route_trips["trip_id"])
        if route_trip_ids:
            stop_deps = stop_deps[stop_deps["trip_id"].isin(route_trip_ids)]

    if stop_deps.empty:
        return _generate_mock_departures(stop_id, limit)

    stop_deps["dep_minutes"] = stop_deps["departure_time"].apply(_parse_gtfs_time)
    upcoming = stop_deps[stop_deps["dep_minutes"] >= current_minutes].nsmallest(limit, "dep_minutes")

    results = []
    for _, row in upcoming.iterrows():
        mins = row["dep_minutes"]
        results.append({
            "stop_id": str(stop_id),
            "trip_id": str(row.get("trip_id", "")),
            "departure_time": _format_gtfs_time(mins),
            "minutes_until": mins - current_minutes,
        })

    return results if results else _generate_mock_departures(stop_id, limit)


def get_trip_arrival_at_stop(gtfs: dict, trip_id: str, stop_id: str) -> Optional[str]:
    """Look up arrival time for a specific trip at a specific stop.

    Returns formatted "HH:MM" string or None if not found.
    """
    stop_times = gtfs.get("stop_times", pd.DataFrame())
    if stop_times.empty:
        return None

    match = stop_times[
        (stop_times["trip_id"].astype(str) == str(trip_id)) &
        (stop_times["stop_id"] == str(stop_id))
    ]
    if match.empty:
        return None

    arrival = match.iloc[0].get("arrival_time")
    if pd.isna(arrival):
        return None

    minutes = _parse_gtfs_time(str(arrival))
    return _format_gtfs_time(minutes)


def _generate_mock_departures(stop_id: str, limit: int) -> list[dict]:
    """Generate realistic mock departure times."""
    now = datetime.now()
    results = []
    for i in range(limit):
        wait = 3 + i * 5  # Every ~5 minutes
        dep_time = now.hour * 60 + now.minute + wait
        h, m = divmod(dep_time % 1440, 60)
        results.append({
            "stop_id": stop_id,
            "trip_id": f"mock_{i}",
            "departure_time": f"{h:02d}:{m:02d}",
            "minutes_until": wait,
        })
    return results


# Major TTC streetcar routes — coordinates follow actual street grid (straight roads).
# Each route includes key station stops for map labels/dots.
TTC_STREETCAR_ROUTES = [
    {
        "route_id": "501", "short_name": "501", "long_name": "Queen",
        "color": "#DD3333",
        "coordinates": [
            [-79.5354, 43.6261],  # Long Branch loop
            [-79.5200, 43.6270],  # Lake Shore Blvd
            [-79.4940, 43.6350],  # Humber loop
            [-79.4780, 43.6395],  # Roncesvalles turn onto Queen
            [-79.4526, 43.6434],  # Dufferin & Queen
            [-79.4356, 43.6461],  # Ossington & Queen
            [-79.4110, 43.6488],  # Bathurst & Queen
            [-79.4037, 43.6497],  # Spadina & Queen
            [-79.3885, 43.6510],  # University & Queen
            [-79.3793, 43.6519],  # Yonge & Queen
            [-79.3720, 43.6525],  # Church & Queen
            [-79.3584, 43.6537],  # Parliament & Queen
            [-79.3451, 43.6558],  # Broadview turn onto Queen E
            [-79.3228, 43.6650],  # Coxwell & Queen
            [-79.3060, 43.6690],  # Woodbine & Queen
            [-79.2935, 43.6730],  # Neville Park loop
        ],
        "stations": [
            {"stop_id": "SC_501_HUM", "stop_name": "Humber Loop", "stop_lat": 43.6350, "stop_lon": -79.4940},
            {"stop_id": "SC_501_DUF", "stop_name": "Dufferin", "stop_lat": 43.6434, "stop_lon": -79.4526},
            {"stop_id": "SC_501_BTH", "stop_name": "Bathurst", "stop_lat": 43.6488, "stop_lon": -79.4110},
            {"stop_id": "SC_501_SPA", "stop_name": "Spadina", "stop_lat": 43.6497, "stop_lon": -79.4037},
            {"stop_id": "SC_501_YNG", "stop_name": "Queen & Yonge", "stop_lat": 43.6519, "stop_lon": -79.3793},
            {"stop_id": "SC_501_BRD", "stop_name": "Broadview", "stop_lat": 43.6558, "stop_lon": -79.3451},
            {"stop_id": "SC_501_NEV", "stop_name": "Neville Park", "stop_lat": 43.6730, "stop_lon": -79.2935},
        ],
    },
    {
        "route_id": "504", "short_name": "504", "long_name": "King",
        "color": "#DD3333",
        "coordinates": [
            [-79.4526, 43.6399],  # Dundas West station
            [-79.4356, 43.6399],  # Dufferin & King
            [-79.4110, 43.6400],  # Bathurst & King
            [-79.4037, 43.6400],  # Spadina & King
            [-79.3885, 43.6427],  # University & King
            [-79.3782, 43.6449],  # Yonge & King
            [-79.3720, 43.6449],  # Church & King
            [-79.3620, 43.6449],  # Jarvis & King
            [-79.3520, 43.6470],  # Parliament & King
            [-79.3451, 43.6520],  # Broadview turn
            [-79.3380, 43.6570],  # Broadview station
        ],
        "stations": [
            {"stop_id": "SC_504_DDW", "stop_name": "Dundas West", "stop_lat": 43.6399, "stop_lon": -79.4526},
            {"stop_id": "SC_504_BTH", "stop_name": "Bathurst", "stop_lat": 43.6400, "stop_lon": -79.4110},
            {"stop_id": "SC_504_SPA", "stop_name": "Spadina", "stop_lat": 43.6400, "stop_lon": -79.4037},
            {"stop_id": "SC_504_YNG", "stop_name": "King & Yonge", "stop_lat": 43.6449, "stop_lon": -79.3782},
            {"stop_id": "SC_504_BRD", "stop_name": "Broadview", "stop_lat": 43.6570, "stop_lon": -79.3380},
        ],
    },
    {
        "route_id": "505", "short_name": "505", "long_name": "Dundas",
        "color": "#DD3333",
        "coordinates": [
            [-79.4526, 43.6567],  # Dundas West station
            [-79.4356, 43.6560],  # Ossington & Dundas
            [-79.4110, 43.6555],  # Bathurst & Dundas
            [-79.4037, 43.6553],  # Spadina & Dundas
            [-79.3885, 43.6550],  # University & Dundas
            [-79.3808, 43.6555],  # Yonge & Dundas
            [-79.3720, 43.6560],  # Church & Dundas
            [-79.3584, 43.6570],  # Parliament & Dundas
            [-79.3451, 43.6580],  # Broadview & Dundas
        ],
        "stations": [
            {"stop_id": "SC_505_DDW", "stop_name": "Dundas West", "stop_lat": 43.6567, "stop_lon": -79.4526},
            {"stop_id": "SC_505_YNG", "stop_name": "Dundas & Yonge", "stop_lat": 43.6555, "stop_lon": -79.3808},
            {"stop_id": "SC_505_BRD", "stop_name": "Broadview", "stop_lat": 43.6580, "stop_lon": -79.3451},
        ],
    },
    {
        "route_id": "506", "short_name": "506", "long_name": "Carlton",
        "color": "#DD3333",
        "coordinates": [
            [-79.4200, 43.6565],  # Lansdowne & College
            [-79.4110, 43.6575],  # Ossington & College
            [-79.4037, 43.6585],  # Bathurst & College
            [-79.3921, 43.6598],  # Spadina & College
            [-79.3827, 43.6610],  # College station (University)
            [-79.3760, 43.6618],  # Yonge & Carlton
            [-79.3686, 43.6625],  # Sherbourne & Carlton
            [-79.3584, 43.6635],  # Parliament & Carlton
            [-79.3451, 43.6665],  # Gerrard & Broadview turn
            [-79.3302, 43.6785],  # Coxwell & Gerrard
            [-79.3012, 43.6840],  # Main Street area
        ],
        "stations": [
            {"stop_id": "SC_506_BTH", "stop_name": "Bathurst", "stop_lat": 43.6585, "stop_lon": -79.4037},
            {"stop_id": "SC_506_COL", "stop_name": "College", "stop_lat": 43.6610, "stop_lon": -79.3827},
            {"stop_id": "SC_506_YNG", "stop_name": "Carlton & Yonge", "stop_lat": 43.6618, "stop_lon": -79.3760},
            {"stop_id": "SC_506_BRD", "stop_name": "Broadview", "stop_lat": 43.6665, "stop_lon": -79.3451},
            {"stop_id": "SC_506_MN", "stop_name": "Main Street", "stop_lat": 43.6840, "stop_lon": -79.3012},
        ],
    },
    {
        "route_id": "509", "short_name": "509", "long_name": "Harbourfront",
        "color": "#DD3333",
        "coordinates": [
            [-79.3806, 43.6453],  # Union Station
            [-79.3840, 43.6390],  # Queens Quay & Bay
            [-79.3900, 43.6380],  # Queens Quay & Rees
            [-79.3960, 43.6375],  # Queens Quay & Spadina
            [-79.4030, 43.6370],  # Queens Quay & Bathurst
            [-79.4130, 43.6360],  # Exhibition loop
        ],
        "stations": [
            {"stop_id": "SC_509_UNI", "stop_name": "Union", "stop_lat": 43.6453, "stop_lon": -79.3806},
            {"stop_id": "SC_509_QQS", "stop_name": "Queens Quay & Spadina", "stop_lat": 43.6375, "stop_lon": -79.3960},
            {"stop_id": "SC_509_EXH", "stop_name": "Exhibition", "stop_lat": 43.6360, "stop_lon": -79.4130},
        ],
    },
    {
        "route_id": "510", "short_name": "510", "long_name": "Spadina",
        "color": "#DD3333",
        "coordinates": [
            [-79.4037, 43.6672],  # Spadina station (subway)
            [-79.4010, 43.6598],  # Spadina & College
            [-79.3990, 43.6530],  # Spadina & Dundas
            [-79.3970, 43.6497],  # Spadina & Queen
            [-79.3955, 43.6449],  # Spadina & King
            [-79.3940, 43.6400],  # Spadina & Front
            [-79.3920, 43.6375],  # Spadina & Queens Quay
        ],
        "stations": [
            {"stop_id": "SC_510_SPA", "stop_name": "Spadina Stn", "stop_lat": 43.6672, "stop_lon": -79.4037},
            {"stop_id": "SC_510_COL", "stop_name": "College", "stop_lat": 43.6598, "stop_lon": -79.4010},
            {"stop_id": "SC_510_QUE", "stop_name": "Queen", "stop_lat": 43.6497, "stop_lon": -79.3990},
            {"stop_id": "SC_510_KNG", "stop_name": "King", "stop_lat": 43.6449, "stop_lon": -79.3955},
            {"stop_id": "SC_510_QQY", "stop_name": "Queens Quay", "stop_lat": 43.6375, "stop_lon": -79.3920},
        ],
    },
    {
        "route_id": "512", "short_name": "512", "long_name": "St Clair",
        "color": "#DD3333",
        "coordinates": [
            [-79.4650, 43.6780],  # Gunn's Loop (west)
            [-79.4500, 43.6790],  # Keele & St Clair
            [-79.4356, 43.6800],  # Lansdowne & St Clair
            [-79.4200, 43.6815],  # Dufferin & St Clair
            [-79.4150, 43.6825],  # St Clair West station
            [-79.4037, 43.6840],  # Bathurst & St Clair
            [-79.3934, 43.6860],  # Yonge & St Clair
            [-79.3800, 43.6870],  # Mt Pleasant & St Clair
        ],
        "stations": [
            {"stop_id": "SC_512_GUN", "stop_name": "Gunn's Loop", "stop_lat": 43.6780, "stop_lon": -79.4650},
            {"stop_id": "SC_512_DUF", "stop_name": "Dufferin", "stop_lat": 43.6815, "stop_lon": -79.4200},
            {"stop_id": "SC_512_SCW", "stop_name": "St Clair West Stn", "stop_lat": 43.6825, "stop_lon": -79.4150},
            {"stop_id": "SC_512_YNG", "stop_name": "Yonge & St Clair", "stop_lat": 43.6860, "stop_lon": -79.3934},
        ],
    },
]

# UP Express route (Union → Pearson Airport)
UP_EXPRESS_ROUTE = {
    "route_id": "UP", "short_name": "UP", "long_name": "UP Express",
    "color": "#1E3A8A",
    "coordinates": [
        [-79.3806, 43.6453],  # Union Station
        [-79.3870, 43.6460],  # west along rail corridor
        [-79.3950, 43.6470],
        [-79.4050, 43.6485],
        [-79.4150, 43.6510],
        [-79.4250, 43.6540],  # curving northwest
        [-79.4350, 43.6565],
        [-79.4450, 43.6590],
        [-79.4550, 43.6615],
        [-79.4620, 43.6635],  # Bloor GO area
        [-79.4700, 43.6660],
        [-79.4800, 43.6700],
        [-79.4870, 43.6740],
        [-79.4900, 43.6780],
        [-79.4920, 43.6810],  # curving north
        [-79.4940, 43.6850],
        [-79.4945, 43.6880],  # Weston GO area
        [-79.4960, 43.6920],
        [-79.4980, 43.6970],
        [-79.5020, 43.7020],
        [-79.5070, 43.7070],
        [-79.5130, 43.7120],  # northwest toward Pearson
        [-79.5200, 43.7160],
        [-79.5300, 43.7200],
        [-79.5420, 43.7250],
        [-79.5550, 43.7300],
        [-79.5700, 43.7350],
        [-79.5850, 43.7380],
        [-79.6000, 43.7400],
        [-79.6110, 43.7410],  # Pearson Terminal 1
    ],
    "stations": [
        {"stop_id": "UP_UNION", "stop_name": "Union", "stop_lat": 43.6453, "stop_lon": -79.3806},
        {"stop_id": "UP_BLOOR", "stop_name": "Bloor", "stop_lat": 43.6635, "stop_lon": -79.4620},
        {"stop_id": "UP_WESTON", "stop_name": "Weston", "stop_lat": 43.6880, "stop_lon": -79.4945},
        {"stop_id": "UP_PEARSON", "stop_name": "Pearson Airport", "stop_lat": 43.7410, "stop_lon": -79.6110},
    ],
}

TTC_LINE_INFO = {
    "1": {"name": "Line 1 Yonge-University", "color": "#F0CC49"},
    "2": {"name": "Line 2 Bloor-Danforth", "color": "#549F4D"},
    "4": {"name": "Line 4 Sheppard", "color": "#9C246E"},
    "5": {"name": "Line 5 Eglinton", "color": "#DE7731"},
    "6": {"name": "Line 6 Finch West", "color": "#959595"},
}

# Transfer connections between TTC rapid transit lines.
# Each entry maps a (from_line, to_line) pair to a list of interchange stations.
# gtfs_ids: real GTFS stop IDs per line at that station (checked against _rapid_index)
# fallback_ids: hardcoded TTC_SUBWAY_STATIONS stop IDs per line
TRANSFER_CONNECTIONS: dict[tuple[str, str], list[dict]] = {
    ("1", "2"): [
        {"name": "Bloor-Yonge", "gtfs_ids": {"1": ["13863", "13864"], "2": ["13755", "13756"]},
         "fallback_ids": {"1": "YU_BLRY", "2": "BD_BLRY"}, "lat": 43.6709, "lng": -79.3857, "time_min": 3},
        {"name": "St George", "gtfs_ids": {"1": ["13857", "13858"], "2": ["13855", "13856"]},
         "fallback_ids": {"1": "YU_STGR", "2": "BD_STGR"}, "lat": 43.6683, "lng": -79.3997, "time_min": 3},
        {"name": "Spadina", "gtfs_ids": {"1": ["13853", "13854"], "2": ["13851", "13852"]},
         "fallback_ids": {"1": "YU_SPAD", "2": "BD_SPAD"}, "lat": 43.6672, "lng": -79.4037, "time_min": 3},
    ],
    ("1", "4"): [
        {"name": "Sheppard-Yonge", "gtfs_ids": {"1": ["13859", "13860"], "4": ["13861", "13862"]},
         "fallback_ids": {"1": "YU_SHEPY", "4": "SH_SHPY"}, "lat": 43.7615, "lng": -79.4111, "time_min": 4},
    ],
    ("1", "5"): [
        {"name": "Eglinton", "gtfs_ids": {"1": ["13795", "13796"], "5": ["16073", "16074"]},
         "fallback_ids": {"1": "YU_EGLN", "5": "EC_EGLN"}, "lat": 43.7064, "lng": -79.3988, "time_min": 5},
    ],
    ("2", "5"): [
        {"name": "Kennedy", "gtfs_ids": {"2": ["13865", "14947"], "5": ["16081", "16082"]},
         "fallback_ids": {"2": "BD_KNDY", "5": "EC_KNDY"}, "lat": 43.7326, "lng": -79.2637, "time_min": 5},
    ],
    ("1", "6"): [
        {"name": "Finch West", "gtfs_ids": {"1": [], "6": []},
         "fallback_ids": {"1": "YU_FNWT", "6": "FW_FNCH"}, "lat": 43.7649, "lng": -79.4912, "time_min": 5},
    ],
}
# Add reverse direction mappings
for (_a, _b), _stations in list(TRANSFER_CONNECTIONS.items()):
    TRANSFER_CONNECTIONS[(_b, _a)] = _stations


def find_transfer_stations(from_line: str, to_line: str) -> list[dict]:
    """Return list of transfer station dicts connecting two lines, or empty list."""
    return TRANSFER_CONNECTIONS.get((str(from_line), str(to_line)), [])


def resolve_transfer_stop_id(gtfs: dict, transfer_station: dict, line_id: str) -> str:
    """Pick a valid GTFS stop_id for a given line at a transfer station.

    Checks real GTFS IDs against _rapid_index first, falls back to hardcoded IDs.
    """
    rapid_index = gtfs.get("_rapid_index", {})
    line_id = str(line_id)

    # Try real GTFS IDs first
    gtfs_ids = transfer_station.get("gtfs_ids", {}).get(line_id, [])
    for sid in gtfs_ids:
        if sid in rapid_index:
            return sid

    # Fallback to hardcoded TTC_SUBWAY_STATIONS IDs
    fallback_id = transfer_station.get("fallback_ids", {}).get(line_id, "")
    return fallback_id


def get_line_stations(gtfs: dict, line_id: str) -> list[dict]:
    """Get ordered list of stations for a TTC rapid transit line.

    Returns list of {stop_id, stop_name, lat, lng} in route order.
    """
    # Use hardcoded stations (reliable order)
    stations = [
        {"stop_id": s["stop_id"], "stop_name": s["stop_name"], "lat": s["stop_lat"], "lng": s["stop_lon"]}
        for s in TTC_SUBWAY_STATIONS
        if str(s.get("route_id")) == str(line_id)
    ]
    return stations


def get_intermediate_stops(gtfs: dict, route_id: str, board_stop_id: str, alight_stop_id: str) -> list[dict]:
    """Get ordered list of intermediate stops between board and alight (inclusive).

    Uses TTC_SUBWAY_STATIONS for subway lines, falls back to stop_times+trips for bus/streetcar.
    Returns list of {stop_id, stop_name, lat, lng}.
    """
    # Try hardcoded subway stations first (reliable order)
    line_stations = [
        s for s in TTC_SUBWAY_STATIONS
        if str(s.get("route_id")) == str(route_id)
    ]
    if line_stations:
        board_idx = next((i for i, s in enumerate(line_stations) if s["stop_id"] == board_stop_id), None)
        alight_idx = next((i for i, s in enumerate(line_stations) if s["stop_id"] == alight_stop_id), None)
        if board_idx is not None and alight_idx is not None:
            lo, hi = min(board_idx, alight_idx), max(board_idx, alight_idx)
            subset = line_stations[lo:hi + 1]
            if board_idx > alight_idx:
                subset = list(reversed(subset))
            return [
                {"stop_id": s["stop_id"], "stop_name": s["stop_name"],
                 "lat": s["stop_lat"], "lng": s["stop_lon"]}
                for s in subset
            ]

    # Fallback: use GTFS stop_times to find ordered stops on a trip for this route
    stop_times_df = gtfs.get("stop_times", pd.DataFrame())
    trips_df = gtfs.get("trips", pd.DataFrame())
    stops_df = gtfs.get("stops", pd.DataFrame())

    if stop_times_df.empty or trips_df.empty or stops_df.empty:
        return []

    route_trips = trips_df[trips_df["route_id"].astype(str) == str(route_id)]
    if route_trips.empty:
        return []

    # Try each trip until we find one that visits both stops in order
    for _, trip_row in route_trips.head(20).iterrows():
        trip_id = trip_row["trip_id"]
        trip_st = stop_times_df[stop_times_df["trip_id"] == trip_id].sort_values("stop_sequence")
        stop_ids_in_trip = list(trip_st["stop_id"])

        board_pos = next((i for i, sid in enumerate(stop_ids_in_trip) if sid == str(board_stop_id)), None)
        alight_pos = next((i for i, sid in enumerate(stop_ids_in_trip) if sid == str(alight_stop_id)), None)

        if board_pos is not None and alight_pos is not None and board_pos < alight_pos:
            subset_ids = stop_ids_in_trip[board_pos:alight_pos + 1]
            lat_col = "stop_lat" if "stop_lat" in stops_df.columns else "latitude"
            lng_col = "stop_lon" if "stop_lon" in stops_df.columns else "longitude"

            result = []
            for sid in subset_ids:
                row = stops_df[stops_df["stop_id"] == sid]
                if not row.empty:
                    r = row.iloc[0]
                    result.append({
                        "stop_id": sid,
                        "stop_name": str(r.get("stop_name", "Unknown")),
                        "lat": float(r[lat_col]),
                        "lng": float(r[lng_col]),
                    })
            if result:
                return result

    return []


def find_transit_route(gtfs: dict, origin_stop_id: str, dest_stop_id: str, route_id: Optional[str] = None) -> Optional[dict]:
    """Find a transit route connecting two stops.

    route_id: if provided, used directly for shape/trip lookup (required for real GTFS
    since stops.txt has no route_id column).
    """
    stops = gtfs["stops"]
    stop_times = gtfs.get("stop_times", pd.DataFrame())

    # Get stop coordinates
    lat_col = "stop_lat" if "stop_lat" in stops.columns else "latitude"
    lng_col = "stop_lon" if "stop_lon" in stops.columns else "longitude"

    origin_stop = stops[stops["stop_id"] == str(origin_stop_id)]
    dest_stop = stops[stops["stop_id"] == str(dest_stop_id)]

    if origin_stop.empty or dest_stop.empty:
        return None

    origin_row = origin_stop.iloc[0]
    dest_row = dest_stop.iloc[0]

    # Use provided route_id, or try to get from stop data (fallback mode)
    route_id_str = str(route_id) if route_id else str(origin_row.get("route_id", ""))

    # If still empty, resolve from stop_times → trips
    if not route_id_str and not stop_times.empty:
        trips_df = gtfs.get("trips", pd.DataFrame())
        st = stop_times[stop_times["stop_id"] == str(origin_stop_id)]
        if not st.empty and not trips_df.empty:
            trip_id = st.iloc[0]["trip_id"]
            trip = trips_df[trips_df["trip_id"] == trip_id]
            if not trip.empty:
                route_id_str = str(trip.iloc[0]["route_id"])

    same_line = bool(route_id_str)

    # Get intermediate stops for accurate distance and geometry
    intermediate = get_intermediate_stops(gtfs, route_id_str, origin_stop_id, dest_stop_id)
    logger.info(f"find_transit_route: route_id={route_id_str}, intermediate={len(intermediate)} stops")

    if len(intermediate) >= 2:
        # Sum haversine between consecutive intermediate stops for real track distance
        distance = 0.0
        for k in range(len(intermediate) - 1):
            distance += haversine(
                intermediate[k]["lat"], intermediate[k]["lng"],
                intermediate[k + 1]["lat"], intermediate[k + 1]["lng"],
            )
        # Use GTFS shapes for detailed track geometry (curves between stations)
        shape_geom = get_route_shape_segment(
            gtfs, route_id_str,
            intermediate[0]["lat"], intermediate[0]["lng"],
            intermediate[-1]["lat"], intermediate[-1]["lng"],
        )
        if shape_geom and len(shape_geom["coordinates"]) >= 2:
            logger.info(f"find_transit_route: using GTFS shape with {len(shape_geom['coordinates'])} points")
            geometry = shape_geom
        else:
            logger.info(f"find_transit_route: GTFS shape not found, using {len(intermediate)} station points")
            # Fallback: connect intermediate stops with straight lines
            geometry = {
                "type": "LineString",
                "coordinates": [[s["lng"], s["lat"]] for s in intermediate],
            }
    else:
        # Fallback to straight-line haversine
        distance = haversine(origin_row[lat_col], origin_row[lng_col], dest_row[lat_col], dest_row[lng_col])
        # Try full route shape
        shape = get_route_shape(gtfs, route_id_str)
        if shape:
            geometry = shape
        else:
            geometry = {
                "type": "LineString",
                "coordinates": [
                    [origin_row[lng_col], origin_row[lat_col]],
                    [dest_row[lng_col], dest_row[lat_col]],
                ]
            }

    # Estimate duration: ~30 km/h average subway speed
    estimated_duration = round(distance / 0.5, 1)  # distance / (30 km/h / 60 min)

    # Resolve route name from routes DataFrame if not already on the stop
    line_name = origin_row.get("line") or None
    if not line_name and route_id_str:
        routes_df = gtfs.get("routes", pd.DataFrame())
        if not routes_df.empty:
            r = routes_df[routes_df["route_id"].astype(str) == route_id_str]
            if not r.empty:
                sn = str(r.iloc[0].get("route_short_name", ""))
                ln = str(r.iloc[0].get("route_long_name", ""))
                if ln.lower().startswith("line"):
                    line_name = ln
                elif sn:
                    line_name = f"{sn} {ln}".strip()
                else:
                    line_name = ln or None
    # Also resolve route_id from stop_times/trips if missing
    resolved_route_id = route_id_str
    if not resolved_route_id and not stop_times.empty:
        trips_df = gtfs.get("trips", pd.DataFrame())
        st = stop_times[stop_times["stop_id"] == str(origin_stop_id)]
        if not st.empty and not trips_df.empty:
            trip_id = st.iloc[0]["trip_id"]
            trip = trips_df[trips_df["trip_id"] == trip_id]
            if not trip.empty:
                resolved_route_id = str(trip.iloc[0]["route_id"])
                # Also look up route name if still missing
                if not line_name:
                    routes_df = gtfs.get("routes", pd.DataFrame())
                    if not routes_df.empty:
                        r = routes_df[routes_df["route_id"].astype(str) == resolved_route_id]
                        if not r.empty:
                            sn = str(r.iloc[0].get("route_short_name", ""))
                            ln = str(r.iloc[0].get("route_long_name", ""))
                            if ln.lower().startswith("line"):
                                line_name = ln
                            elif sn:
                                line_name = f"{sn} {ln}".strip()
                            else:
                                line_name = ln or None

    route_info = {
        "origin_stop": origin_stop_id,
        "dest_stop": dest_stop_id,
        "origin_name": origin_row.get("stop_name", "Unknown"),
        "dest_name": dest_row.get("stop_name", "Unknown"),
        "distance_km": round(distance, 2),
        "estimated_duration_min": estimated_duration,
        "line": line_name or "TTC",
        "route_id": resolved_route_id or route_id_str,
        "transfers": 0 if same_line else 1,
        "geometry": geometry,
    }

    return route_info
