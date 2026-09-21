"""Validation against a real refinery: IndianOil's Paradip (15 mtpa, Nelson 12.2).

(1) Nelson complexity from the published unit list, and (2) which crude
basket loads the published coker and FCC capacities.  Sources: Oil & Gas
Journal, "Indian Oil commissions Paradip refinery" (see docs/VALIDATION.md).

Run: python examples/paradip_check.py
"""
from refinery_design.benchmarks import CDU_MTPA, REPORTED_NCI, paradip_blend_fit, paradip_nci

print("NELSON COMPLEXITY, Paradip published unit list (reported: %.1f)" % REPORTED_NCI)
print(f"{'factor set':10s} {'VDU/CDU':>8s} {'units counted':>28s} {'NCI':>6s} {'vs 12.2':>8s}")
for f in ("1998", "older"):
    for v, amb, label in ((0.6, False, "unambiguous only"), (1.0, False, "unambiguous only"),
                          (0.6, True, "+ ambiguous-unit readings"), (1.0, True, "+ ambiguous-unit readings")):
        n = paradip_nci(f, v, amb)
        print(f"{f:10s} {v:8.1f} {label:>28s} {n:6.2f} {100*(n/REPORTED_NCI-1):+7.1f}%")

print("\nCRUDE BASKET THAT LOADS A 15 MTPA CDU WITH 4.1 MTPA COKER / 4.2 MTPA FCC")
f = paradip_blend_fit()
print(f"  fitted: {100*f['heavy_fraction_vol']:.0f} vol% Cold Lake Blend + {100*(1-f['heavy_fraction_vol']):.0f} vol% Upper Zakum")
print(f"  slate:  API {f['api']:.1f}, {f['sulfur_wt']:.2f} wt% S")
print(f"  vacuum residue {100*f['vr_wt_frac']:.1f}% of crude  (fitted to coker/CDU = {100*f['coker_to_cdu']:.1f}%)")
print(f"  VGO            {100*f['vgo_wt_frac']:.1f}% of crude  (PREDICTION; FCC/CDU published = {100*f['fcc_to_cdu']:.1f}%)")
print(f"  -> implied VR {f['vr_wt_frac']*CDU_MTPA:.2f} Mt/yr, VGO {f['vgo_wt_frac']*CDU_MTPA:.2f} Mt/yr")
