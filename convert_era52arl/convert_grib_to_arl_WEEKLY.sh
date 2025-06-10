#!/bin/bash
# Modified ERA5 chunked data conversion script (supports _p1/_p2/_p3 chunk format)
# Processing logic: Each chunk generates corresponding .arl file independently

# Define target years list (adjustable)
target_years=(1960)

for target_year in "${target_years[@]}"
do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "▷▷ Processing year: $target_year ◁◁"
    
    # Process all chunked files for current year (matching _p* suffix)
    for file_pressure in north_6h_pressure_${target_year}_*_p*.grib
    do
        # 🔍 Extract key identifiers (new naming convention parsing)
        # Example filename: north_6h_pressure_2009_12_p1.grib
        base_name=$(basename "$file_pressure" .grib)   # Remove extension
        file_parts=(${base_name//_/ })                 # Split by _ into array
        yyyy_mm="${file_parts[3]}_${file_parts[4]}"    # Combine year-month (parts 4-5)
        chunk="${file_parts[5]}"                       # Extract chunk identifier (part 6)
        
        # 🎯 Construct output filename (including chunk identifier)
        output_file="north_6h_${yyyy_mm}_${chunk}.arl"
        
        # 1️⃣ Skip existing output files
        if [[ -f "$output_file" ]]; then
            echo "[√] Skipping existing file: $(basename $output_file)"
            continue
        fi
        
        # 2️⃣ Check corresponding surface data file
        file_single="north_6h_single_${yyyy_mm}_${chunk}.grib"
        if [[ ! -f "$file_single" ]]; then
            echo "[×] Missing surface data: $file_single"
            continue
        fi
        
        # 🚀 Execute conversion command
        echo "▷ Converting ${yyyy_mm}_${chunk} chunk..."
        ./era52arl -dera52arl.cfg \
            -i"$file_pressure" \
            -a"$file_single" \
            -f"$file_single" \
            -o"$output_file" \
            -v
        
        # ✅ Verify output
        if [[ $? -eq 0 && -f "$output_file" ]]; then
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "[√√√] Successfully generated: $(basename $output_file) ($(date +%H:%M:%S))"
        else
            echo "[×××] Conversion failed: $file_pressure → $output_file"
        fi
    done
    
    echo "▷▷ Year ${target_year} processing complete ◁◁"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
done

echo "★★★ All years processed successfully ★★★"