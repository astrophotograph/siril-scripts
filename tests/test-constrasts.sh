FILE="/Users/erewhon/AstroPhotos/tmp/Lagoon_Nebula_334x10sec_T22C_2025-05-09_3340s_drizzle_2x_square_UC_BE_PS_CR_SPCC_StarSep_ST_StarComb_DG_UC.fit.tif"

for cutoff in 0.3 0.4 0.5 0.6 0.7
do
  for g in 1 2 3 4 5 6 7
  do
    uv run contrast.py --method sigmoid --gain $g --cutoff $cutoff --output test_${g}_${cutoff}.tif $FILE
  done
done
