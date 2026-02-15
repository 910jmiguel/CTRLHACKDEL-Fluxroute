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
    {"stop_id": "YU_DUND", "stop_name": "Dundas", "stop_lat": 43.6561, "stop_lon": -79.3803, "route_id": "1", "line": "Line 1 Yonge-University"},
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
    {"stop_id": "YU_DWPK", "stop_name": "Downsview Park", "stop_lat": 43.7452, "stop_lon": -79.4784, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_SHPW", "stop_name": "Sheppard West", "stop_lat": 43.7494, "stop_lon": -79.4618, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_FNWT", "stop_name": "Finch West", "stop_lat": 43.7653, "stop_lon": -79.4910, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_YKUN", "stop_name": "York University", "stop_lat": 43.7735, "stop_lon": -79.5009, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_PNVL", "stop_name": "Pioneer Village", "stop_lat": 43.7778, "stop_lon": -79.5105, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_HW407", "stop_name": "Highway 407", "stop_lat": 43.7831, "stop_lon": -79.5231, "route_id": "1", "line": "Line 1 Yonge-University"},
    {"stop_id": "YU_VMC", "stop_name": "Vaughan Metropolitan Centre", "stop_lat": 43.7943, "stop_lon": -79.5273, "route_id": "1", "line": "Line 1 Yonge-University"},
    # Line 2 Bloor-Danforth (BD)
    {"stop_id": "BD_KPLG", "stop_name": "Kipling", "stop_lat": 43.6372, "stop_lon": -79.5361, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_ISLN", "stop_name": "Islington", "stop_lat": 43.6386, "stop_lon": -79.5246, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
    {"stop_id": "BD_RYLK", "stop_name": "Royal York", "stop_lat": 43.6384, "stop_lon": -79.5113, "route_id": "2", "line": "Line 2 Bloor-Danforth"},
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
    {"stop_id": "EC_MTDN", "stop_name": "Mount Dennis", "stop_lat": 43.6870, "stop_lon": -79.5018, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_KEEL", "stop_name": "Keelesdale", "stop_lat": 43.6891, "stop_lon": -79.4836, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_CRST", "stop_name": "Caledonia", "stop_lat": 43.6907, "stop_lon": -79.4686, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_DFFR", "stop_name": "Dufferin", "stop_lat": 43.6938, "stop_lon": -79.4414, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_FAIR", "stop_name": "Fairbank", "stop_lat": 43.6955, "stop_lon": -79.4315, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_OAKW", "stop_name": "Oakwood", "stop_lat": 43.6967, "stop_lon": -79.4245, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_CDVL", "stop_name": "Cedarvale", "stop_lat": 43.6998, "stop_lon": -79.4362, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_FHLS", "stop_name": "Forest Hill", "stop_lat": 43.6996, "stop_lon": -79.4147, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_CHPL", "stop_name": "Chaplin", "stop_lat": 43.7013, "stop_lon": -79.4062, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_AVEN", "stop_name": "Avenue", "stop_lat": 43.7033, "stop_lon": -79.3983, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_EGLN", "stop_name": "Eglinton", "stop_lat": 43.7057, "stop_lon": -79.3984, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_MTPL", "stop_name": "Mount Pleasant", "stop_lat": 43.7077, "stop_lon": -79.3892, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_LIRD", "stop_name": "Leaside", "stop_lat": 43.7080, "stop_lon": -79.3670, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_LAER", "stop_name": "Laird", "stop_lat": 43.7083, "stop_lon": -79.3580, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_BAYO", "stop_name": "Bayview", "stop_lat": 43.7085, "stop_lon": -79.3490, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_SCNC", "stop_name": "Science Centre", "stop_lat": 43.7090, "stop_lon": -79.3388, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_AMES", "stop_name": "Aga Khan Park & Museum", "stop_lat": 43.7228, "stop_lon": -79.3310, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_ODNN", "stop_name": "O'Connor", "stop_lat": 43.7230, "stop_lon": -79.3230, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_FRMH", "stop_name": "Ferrand", "stop_lat": 43.7230, "stop_lon": -79.3150, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_PHRM", "stop_name": "Pharmacy", "stop_lat": 43.7233, "stop_lon": -79.2980, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_HKME", "stop_name": "Hakimi Lebovic", "stop_lat": 43.7235, "stop_lon": -79.2815, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_WNFR", "stop_name": "Winferd", "stop_lat": 43.7240, "stop_lon": -79.2770, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_IONV", "stop_name": "Ionview", "stop_lat": 43.7260, "stop_lon": -79.2722, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_SLVR", "stop_name": "Sloane", "stop_lat": 43.7285, "stop_lon": -79.2681, "route_id": "5", "line": "Line 5 Eglinton"},
    {"stop_id": "EC_KNDY", "stop_name": "Kennedy", "stop_lat": 43.7326, "stop_lon": -79.2637, "route_id": "5", "line": "Line 5 Eglinton"},
    # Line 6 Finch West LRT (18 stations: Finch West → Humber College)
    {"stop_id": "FW_FNCH", "stop_name": "Finch West", "stop_lat": 43.7649, "stop_lon": -79.4912, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_KEYS", "stop_name": "Keele", "stop_lat": 43.7645, "stop_lon": -79.4970, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_DRFT", "stop_name": "Driftwood", "stop_lat": 43.7641, "stop_lon": -79.5089, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_JANE", "stop_name": "Jane", "stop_lat": 43.7639, "stop_lon": -79.5140, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_SNTN", "stop_name": "Sentinel", "stop_lat": 43.7638, "stop_lon": -79.5213, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_PRKS", "stop_name": "Pearldale", "stop_lat": 43.7637, "stop_lon": -79.5265, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_SGWY", "stop_name": "Signet", "stop_lat": 43.7635, "stop_lon": -79.5352, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_NORW", "stop_name": "Norwood", "stop_lat": 43.7633, "stop_lon": -79.5400, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_WTSN", "stop_name": "Weston", "stop_lat": 43.7631, "stop_lon": -79.5450, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_MTNR", "stop_name": "Martin Grove", "stop_lat": 43.7630, "stop_lon": -79.5520, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_GRBY", "stop_name": "Goreway", "stop_lat": 43.7628, "stop_lon": -79.5570, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_ALBW", "stop_name": "Albion", "stop_lat": 43.7627, "stop_lon": -79.5590, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_KPLG", "stop_name": "Kipling", "stop_lat": 43.7625, "stop_lon": -79.5650, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_MSHL", "stop_name": "Milvan", "stop_lat": 43.7624, "stop_lon": -79.5710, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_WLBY", "stop_name": "Westmore", "stop_lat": 43.7623, "stop_lon": -79.5770, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_NRSK", "stop_name": "Norse", "stop_lat": 43.7622, "stop_lon": -79.5830, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_HMWY", "stop_name": "Highway 27", "stop_lat": 43.7621, "stop_lon": -79.5890, "route_id": "6", "line": "Line 6 Finch West"},
    {"stop_id": "FW_HMBR", "stop_name": "Humber College", "stop_lat": 43.7620, "stop_lon": -79.5940, "route_id": "6", "line": "Line 6 Finch West"},
]


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
            "trips": pd.DataFrame(), "stop_times": pd.DataFrame(), "using_fallback": False}

    files = {
        "stops": "stops.txt",
        "routes": "routes.txt",
        "shapes": "shapes.txt",
        "trips": "trips.txt",
        "stop_times": "stop_times.txt",
    }

    columns_map = {
        "stops": ["stop_id", "stop_name", "stop_lat", "stop_lon", "route_id", "line"],
        "stop_times": ["trip_id", "stop_id", "arrival_time", "departure_time", "stop_sequence"],
        "trips": ["route_id", "service_id", "trip_id", "trip_headsign", "shape_id"],
        "shapes": ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
        "routes": ["route_id", "route_short_name", "route_long_name", "route_color", "route_type"],
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

    # GTFS data available: filter to rapid transit stops
    rapid_route_types = {0, 1, 2}
    rapid_routes = routes_df[routes_df["route_type"].isin(rapid_route_types)]
    if rapid_routes.empty:
        return []

    rapid_route_ids = set(rapid_routes["route_id"].unique())

    # Join through trips -> stop_times to find stops served by rapid transit
    if not trips_df.empty and not stop_times_df.empty:
        rapid_trips = trips_df[trips_df["route_id"].isin(rapid_route_ids)]
        rapid_trip_ids = set(rapid_trips["trip_id"].unique())
        rapid_stop_times = stop_times_df[stop_times_df["trip_id"].isin(rapid_trip_ids)]
        rapid_stop_ids = set(rapid_stop_times["stop_id"].unique())
        rapid_stops = stops[stops["stop_id"].isin(rapid_stop_ids)]
    else:
        # Can't join — return empty
        return []

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
            # Find which route this stop is on
            stop_id = row["stop_id"]
            route_id = None
            line = None
            if not stop_times_df.empty and not trips_df.empty:
                st = stop_times_df[stop_times_df["stop_id"] == stop_id]
                if not st.empty:
                    trip_id = st.iloc[0]["trip_id"]
                    trip = trips_df[trips_df["trip_id"] == trip_id]
                    if not trip.empty:
                        route_id = trip.iloc[0]["route_id"]
                        if route_id in rapid_route_ids:
                            r = rapid_routes[rapid_routes["route_id"] == route_id]
                            if not r.empty:
                                sn = str(r.iloc[0].get("route_short_name", ""))
                                ln = str(r.iloc[0].get("route_long_name", ""))
                                # Avoid "Line 1 Line 1 (...)" duplication
                                if ln.lower().startswith("line"):
                                    line = ln
                                elif sn:
                                    line = f"Line {sn} {ln}".strip()
                                else:
                                    line = ln

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

    results = []
    for _, row in nearby.iterrows():
        stop_id = row.get("stop_id", "")
        stop_name = row.get("stop_name", "Unknown")
        results.append({
            "stop_id": str(stop_id),
            "stop_name": stop_name,
            "lat": row[lat_col],
            "lng": row[lng_col],
            "distance_km": round(row["distance_km"], 3),
            "route_id": row.get("route_id", None),
            "line": row.get("line", None),
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


def get_next_departures(gtfs: dict, stop_id: str, limit: int = 5) -> list[dict]:
    """Get next departures from a stop, handling GTFS 25:00:00 time format."""
    stop_times = gtfs.get("stop_times", pd.DataFrame())
    if stop_times.empty:
        return _generate_mock_departures(stop_id, limit)

    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    stop_deps = stop_times[stop_times["stop_id"].astype(str) == str(stop_id)].copy()
    if stop_deps.empty:
        return _generate_mock_departures(stop_id, limit)

    def parse_gtfs_time(t: str) -> int:
        """Parse GTFS time like '25:30:00' to minutes since midnight."""
        try:
            parts = str(t).split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0

    stop_deps["dep_minutes"] = stop_deps["departure_time"].apply(parse_gtfs_time)
    upcoming = stop_deps[stop_deps["dep_minutes"] >= current_minutes].nsmallest(limit, "dep_minutes")

    results = []
    for _, row in upcoming.iterrows():
        mins = row["dep_minutes"]
        h, m = divmod(mins % 1440, 60)
        results.append({
            "stop_id": str(stop_id),
            "trip_id": str(row.get("trip_id", "")),
            "departure_time": f"{h:02d}:{m:02d}",
            "minutes_until": mins - current_minutes,
        })

    return results if results else _generate_mock_departures(stop_id, limit)


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


TTC_LINE_INFO = {
    "1": {"name": "Line 1 Yonge-University", "color": "#F0CC49"},
    "2": {"name": "Line 2 Bloor-Danforth", "color": "#549F4D"},
    "4": {"name": "Line 4 Sheppard", "color": "#9C246E"},
    "5": {"name": "Line 5 Eglinton", "color": "#DE7731"},
    "6": {"name": "Line 6 Finch West", "color": "#959595"},
}


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
        stop_ids_in_trip = list(trip_st["stop_id"].astype(str))

        board_pos = next((i for i, sid in enumerate(stop_ids_in_trip) if sid == str(board_stop_id)), None)
        alight_pos = next((i for i, sid in enumerate(stop_ids_in_trip) if sid == str(alight_stop_id)), None)

        if board_pos is not None and alight_pos is not None and board_pos < alight_pos:
            subset_ids = stop_ids_in_trip[board_pos:alight_pos + 1]
            lat_col = "stop_lat" if "stop_lat" in stops_df.columns else "latitude"
            lng_col = "stop_lon" if "stop_lon" in stops_df.columns else "longitude"

            result = []
            for sid in subset_ids:
                row = stops_df[stops_df["stop_id"].astype(str) == sid]
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


def find_transit_route(gtfs: dict, origin_stop_id: str, dest_stop_id: str) -> Optional[dict]:
    """Find a transit route connecting two stops."""
    stops = gtfs["stops"]
    stop_times = gtfs.get("stop_times", pd.DataFrame())

    # Get stop coordinates
    lat_col = "stop_lat" if "stop_lat" in stops.columns else "latitude"
    lng_col = "stop_lon" if "stop_lon" in stops.columns else "longitude"

    origin_stop = stops[stops["stop_id"].astype(str) == str(origin_stop_id)]
    dest_stop = stops[stops["stop_id"].astype(str) == str(dest_stop_id)]

    if origin_stop.empty or dest_stop.empty:
        return None

    origin_row = origin_stop.iloc[0]
    dest_row = dest_stop.iloc[0]

    # Check if same line (for fallback data)
    same_line = (origin_row.get("route_id") is not None and
                 origin_row.get("route_id") == dest_row.get("route_id"))

    route_id_str = str(origin_row.get("route_id", ""))

    # Get intermediate stops for accurate distance and geometry
    intermediate = get_intermediate_stops(gtfs, route_id_str, origin_stop_id, dest_stop_id)

    if len(intermediate) >= 2:
        # Sum haversine between consecutive intermediate stops for real track distance
        distance = 0.0
        for k in range(len(intermediate) - 1):
            distance += haversine(
                intermediate[k]["lat"], intermediate[k]["lng"],
                intermediate[k + 1]["lat"], intermediate[k + 1]["lng"],
            )
        # Build geometry as polyline through all intermediate stops
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

    route_info = {
        "origin_stop": origin_stop_id,
        "dest_stop": dest_stop_id,
        "origin_name": origin_row.get("stop_name", "Unknown"),
        "dest_name": dest_row.get("stop_name", "Unknown"),
        "distance_km": round(distance, 2),
        "estimated_duration_min": estimated_duration,
        "line": origin_row.get("line", "Unknown"),
        "route_id": route_id_str,
        "transfers": 0 if same_line else 1,
        "geometry": geometry,
    }

    return route_info
