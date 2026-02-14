#!/bin/bash
# Download GTFS feeds for Greater Toronto Hamilton Area (GTHA) transit agencies
# Usage: ./backend/scripts/download_gtfs.sh

set -e  # Exit on error

echo "Downloading GTFS feeds for GTHA transit agencies..."
cd backend/data/otp/gtfs

# TTC (Toronto Transit Commission)
echo "Downloading TTC GTFS..."
curl -L -o ttc.zip "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/7795b45e-e65a-4465-81fc-c36b9dfff169/resource/cfb6b2b8-6191-41e3-bda1-b175c51148cb/download/opendata_ttc_schedules.zip"

# GO Transit (Metrolinx)
echo "Downloading GO Transit GTFS..."
curl -L -o gotransit.zip "https://www.gotransit.com/static_files/gotransit/assets/Files/GO_GTFS.zip"

# YRT (York Region Transit)
echo "Downloading YRT GTFS..."
curl -L -o yrt.zip "https://www.yrt.ca/google/google_transit.zip"

# MiWay (Mississauga Transit)
echo "Downloading MiWay GTFS..."
curl -L -o miway.zip "http://www.mississauga.ca/file/COM/GoogleTransit.zip"

# Brampton Transit
echo "Downloading Brampton Transit GTFS..."
curl -L -o brampton.zip "https://www.brampton.ca/EN/residents/transit/plan-your-trip/Pages/GoogleTransitFeed.aspx"

# OSM data for walking/cycling routing
echo "Downloading OpenStreetMap data for Ontario..."
curl -L -o ../osm/ontario.osm.pbf "https://download.geofabrik.de/north-america/canada/ontario-latest.osm.pbf"

echo ""
echo "✅ GTFS feeds downloaded successfully!"
echo ""
echo "Next steps:"
echo "1. Validate GTFS feeds at https://gtfsvalidator.mobilitydata.org/"
echo "2. If you have UP Express GTFS, validate and add it as upexpress.zip"
echo "3. Build OTP graph: docker-compose up otp"
echo ""
