#!/usr/bin/env bash
set -e

# RTO - DB, BE, BEW, GAI, LUAS, IE/IR

cd /svcs/transportthing.uk

operators=(
    "Realtime Transport Operators"
    "TFI Local Link"
    "Aircoach"
    "Bernard Kavanagh"
    "City Direct"
    "Citylink"
    "Dublin Coach"
    "Express Bus"
    "JJ Kavanagh"
    "Kearns Transport"
    "Matthews"
    "McGrath Coaches"
    "Nitelink"
    "Slieve Bloom Coach Tours"
    "Small Operators"
    "Swords Express"
    "Wexford Bus"
    "Ferries, Cable Cars, and Regional Flights"
)

for operator in "${operators[@]}"; do
    echo "--- Starting import for: $operator ---"
    docker compose exec web uv run ./manage.py import_gtfs "$operator"
    echo "✅ $operator done"
done

echo "🎉 All imports completed successfully."
