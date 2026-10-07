"""Explicit QA invocation only: platform successor and unchanged Direct evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys
from decimal import Decimal, localcontext

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend/src'), str(ROOT / 'backend')]
from tests.calculation.test_appendix_rc3 import CASES, arguments, values, serialized
from tests.api.test_appendix_rc3_direct_parity import BASELINE, direct_projection
from frp_master_connection.calculation.appendix_rc3 import full_first_row_resistance_rc3, ENGINE_ID, SPEC_ID, GOLDEN_ID
from frp_master_connection.calculation.multirow_equations import full_first_row_resistance
from frp_master_connection.calculation.equations import INTERNAL_DECIMAL_PRECISION

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for case in CASES:
        pair = []
        for si in (False, True):
            trace = full_first_row_resistance_rc3(**arguments(case, si=si))
            actual = values(trace)
            assert {k: serialized(v) for k,v in actual.items()} == {k: Decimal(v) for k,v in case['expected_12'].items()}
            pair.append(actual)
            results.append(dict(case=case['id'], units='SI' if si else 'US',
                                theta_branch=trace.theta_branch.value,
                                values_60={k:str(v) for k,v in actual.items()}))
        assert pair[0] == pair[1]
    args = arguments(CASES[0]); args.pop('row_count')
    args['bolt_count'] = args.pop('bolts_per_row')
    args['net_hole_diameter'] = args.pop('nominal_hole_diameter')
    with localcontext() as ctx:
        ctx.prec = INTERNAL_DECIMAL_PRECISION
        old = full_first_row_resistance(**args)
    assert serialized(old.knt) == Decimal('0.671426574084')
    direct = direct_projection()
    assert direct == BASELINE['expected']
    payload = dict(candidate_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   platform=platform.platform(), engine=ENGINE_ID, spec=SPEC_ID, golden=GOLDEN_ID,
                   geometries=len(CASES), evaluations=len(results),
                   frozen_witness_knt=str(old.knt), successor_witness_knt=results[0]['values_60']['knt'],
                   cases=results, direct_c3_parity=direct)
    (output/'APPENDIX_RC3_PLATFORM_QA.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print('Appendix RC3 independent numerical reference / raw US-SI parity / Direct C3 parity PASS')

if __name__ == '__main__':
    main()
