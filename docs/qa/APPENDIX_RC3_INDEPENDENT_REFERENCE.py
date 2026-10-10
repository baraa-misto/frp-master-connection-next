"""Independent printed-equation ledger. No production/test engine imports."""
from decimal import Decimal as D, localcontext, ROUND_HALF_EVEN
from pathlib import Path
import json

E = Path(__file__).resolve().parent
C = E.parents[1]
MPA_PER_KSI = D('6.89475729316836133672267344534689069378138756277512555025110')
Q = D('0.000000000001')  # Existing RC2 coefficient/report serialization contract.
cases = []
with localcontext() as ctx:
    ctx.prec = 60
    for rows in (2, 3):
        for direction in ('LONGITUDINAL', 'TRANSVERSE'):
            for n in (1, 2, 3):
                w = D('3.25') if n == 1 else D(4 * n)
                g = None if n == 1 else D(2)
                spacing = w if n == 1 else g
                for state in ('nonunit', 'unit', 'below', 'exact', 'above'):
                    e = (D(3) if n == 1 else D('1.6')) if state == 'nonunit' else {
                        'unit': spacing * D('1.25'), 'below': spacing - Q,
                        'exact': spacing, 'above': spacing + Q,
                    }[state]
                    operands = dict(w=str(w), d='.5', dn='.563', t='.5', e1=str(e),
                                    gauge=None if g is None else str(g),
                                    ft_ksi='30' if direction == 'LONGITUDINAL' else '7',
                                    lbr='.5' if rows == 2 else '.4', lap='.9', pitch='.8', time='.7')
                    spr = spacing / D('.5')
                    theta = D('1.5') - D('.5') * spacing / e if e <= spacing else D(1)
                    ratio = (spr - 1) / (spr + 1)
                    product = ratio * theta
                    knt = (1 + D('.5') * (spr - D('1.5') * product)) / (w / (n * D('.5')) - 1)
                    kop = 1 + D('.5') * (1 + (1 - 1 / spr) ** 3)
                    a = knt * w / (n * D('.5'))
                    b = kop / (1 - n * D('.563') / w)
                    lbr = D(operands['lbr'])
                    denominator = a * lbr + b * (1 - lbr)
                    ft = D(operands['ft_ksi']) * MPA_PER_KSI
                    # Converted physical area in mm2 and stress in MPa => N.
                    rn = (w * D('25.4')) * (D('.5') * D('25.4')) * ft / denominator
                    phi = D('.5') if direction == 'LONGITUDINAL' else D('.45')
                    rd = rn * D('.9') * D('.8') * phi * D('.7')
                    vals = dict(spr=spr, theta=theta, ratio=ratio, ratio_times_theta=product,
                                knt=knt, kop=kop, coefficient_a=a, coefficient_b=b,
                                denominator=denominator, nominal_n=rn, design_n=rd)
                    cases.append(dict(id=f'{direction}-n{n}-rows{rows}-{state}', direction=direction,
                                      bolts_per_row=n, row_count=rows, state=state, inputs=operands,
                                      equation=('CA8-2' if direction == 'LONGITUDINAL' else 'CA8-7') if n == 1 else ('CA8-4' if direction == 'LONGITUDINAL' else 'CA8-9'),
                                      theta_branch=f'E1_OVER_{"W" if n == 1 else "G"}_{"LE" if e <= spacing else "GE"}_1',
                                      reference_60={k: str(v) for k,v in vals.items()},
                                      expected_12={k: str(v.quantize(Q, rounding=ROUND_HALF_EVEN)) for k,v in vals.items()}))
data = dict(identity='calculation-slice-2-appendix-golden-rc3', spec='CS2-APPENDIX-RC3',
            engine='asce74-23-ch8-multirow-appendix-corrected-rc3.dev1',
            predecessor='asce74-23-ch8-multirow-rc2.dev1', precision=60,
            serialization='1E-12 ROUND_HALF_EVEN (historical RC2 test contract)',
            reference_method='Independent Decimal arithmetic; no engine imports',
            units=dict(in_to_mm='25.4', ksi_to_mpa=str(MPA_PER_KSI)),
            scope='Coefficient QA only; synthetic strengths do not qualify any design', cases=cases)
dest=C/'backend/tests/golden/calculation_slice_2_appendix_golden_benchmarks_rc3.json'
dest.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
ledger = ['# Independent Appendix RC3 ledger', '',
          'Every case below was calculated by an external script that imports only Python Decimal, pathlib and JSON. No production engine or test helper supplies expected values.', '',
          'Precision: 60 decimal digits. Existing RC2 serialization: 1E-12, ROUND_HALF_EVEN. Full precision references remain in the new golden. Conversion factors: 25.4 mm/in and the governed 60-digit ksi/MPa factor recorded in the golden.', '',
          'Printed grouping: r=(Sprâˆ’1)/(Spr+1); Knt=[1+Ci(Sprâˆ’1.5rÎ˜)]/[w/(nd)âˆ’1]; Kop=1+Cop[1+(1âˆ’1/Spr)^3]. A=Knt*w/(nd); B=Kop/(1âˆ’n*dn/w); Rn=w*t*Ft/[A*Lbr+B*(1âˆ’Lbr)]; Rd=Rn*Clap*Cdelta*phi*lambda.', '',
          'Ci=Cop=0.5 for these SHAPE references. Lbr=0.5 for two rows, 0.4 for three rows (unchanged Table C8-1 values); Clap=0.9, Cdelta=0.8, lambda=0.7 are explicitly supplied synthetic test factors. Phi L=0.5, T=0.45. No demand, status or qualification is inferred.', '',
          'The 3.25-in width witness is mathematical coefficient QA and is not a resolved Direct physical width.', '']
for case in cases:
    ledger += [f'## {case["id"]}', '', f'Equation {case["equation"]}; branch {case["theta_branch"]}.', '',
               'Operands (inches, ksi, dimensionless factors): `'+json.dumps(case['inputs'])+'`.', '']
    ledger += [f'- {k}: `{v}`' for k,v in case['reference_60'].items()]
    ledger += ['']
(E/'SLICE2_APPENDIX_CORRECTION_INDEPENDENT_LEDGER.md').write_text('\n'.join(ledger),encoding='utf-8')
(E/'SLICE2_SUCCESSOR_GOLDEN_BENCHMARKS.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(f'Independent references: {len(cases)} geometries, 120 U.S./SI evaluations')
