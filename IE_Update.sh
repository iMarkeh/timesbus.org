#!/usr/bin/env bash
set -e

# RTO - DB, BE, BEW, GAI, LUAS, IE/IR

cd /svcs/transportthing.uk

operators=(
    "Aircoach"
    "Ashbourne Connect"
    "Bernard Kavanagh"
    "City Direct"
    "Citylink"
    "Corduff Coaches"
    "Dublin Coach"
    "Express Bus"
    "Ferries, Cable Cars, and Regional Flights"
    "Irish NaPTAN"
    "JJ Kavanagh"
    "Kearns Transport"
    "Matthews"
    "McGrath Coaches"
    "Nitelink"
    "Realtime Transport Operators"
    "Slieve Bloom Coach Tours"
    "Small Operators"
    "Swords Express"
    "TFI Local Link"
    "Westlink Coaches"
    "Wexford Bus"
)

for operator in "${operators[@]}"; do
    echo "--- Starting import for: $operator ---"
    docker compose exec web uv run ./manage.py import_gtfs "$operator"
    echo "✅ $operator done"
done

echo "🎉 All imports completed successfully."
