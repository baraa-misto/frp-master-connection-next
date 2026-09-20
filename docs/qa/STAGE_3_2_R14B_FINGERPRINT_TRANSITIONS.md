# Stage 3.2-R14B material-basis fingerprint transitions

Stage 3.2-R14B changes canonical material-orientation identity only. The matched
pre/post tests reconstruct the complete canonical payload for every row below and
prove exact equality of physical geometry, force vectors, demand, resistance,
utilization, applicability, status, and result identity. `FLAT` shares the default
column support/Tee topology and therefore shares those parent preview transitions;
its connected Flat Plate basis remains unchanged.

| Fixture | Identity | Before | After | Exact corrected region(s) in the canonical payload |
| --- | --- | --- | --- | --- |
| DEFAULT_COLUMN / FLAT | Interface A preview | `b0dd56d48a497eacc7990a37a7b3810fd437d88999464a04e9db5cdc88b0b3d4` | `5d1b9038b75a641b5065eb023572c3919d5282683689f3c002f4973d13aa6567` | Tee `STEM`; W/I `WEB` |
| DEFAULT_COLUMN / FLAT | Interface B preview | `552b502f700c0e0d87699e3bb180126e643a5e08a8ddf0b1682fe8b50dbbaf97` | `709e6ab3c9092f37eba34f12310af21adad3a077ac5360e93e111f7dd4770191` | Tee `STEM`; W/I `WEB` |
| DEFAULT_BEAM | Interface A preview | `2c73c4e2fd30868076d15c2a1a99897b7af910c7fd6b02b0fc2d7193af806c04` | `aafaaf5789ad3541535e52d5c7f188e13640b7fe0bc713066e86737e8842942c` | Tee `STEM`; W/I `WEB` |
| DEFAULT_BEAM | Interface B preview | `8f01be2c104ec11d451d06c7669346c6f2b4eb282dd1e1f7f534aa582a903561` | `050c5f144320275390448a18ad5c0cc4a5b99c782fd30e07435866c5f9e4481e` | Tee `STEM`; W/I `WEB` |
| ANGLE | Interface A preview | `5dda37a9ab8a76efeb069cd5978836635c2bc8c1e75a9f8828245aaff5f76e30` | `c23effca7201b03e3a29b40db4790efe231646e9be5f0be7890d13f651a37d34` | Angle `LEG_2`; Tee `STEM`; W/I `WEB` |
| ANGLE | Interface B preview | `ffe1c6903b79b2b1823a0d925f9ed230c38410b3b3d6f08081b336239dcc5674` | `28e55f348274faab6e9bc89048d7c05ffba45e24ea5d23a65f89a9cbde4f5570` | Angle `LEG_2`; Tee `STEM`; W/I `WEB` |
| CHANNEL | Interface A preview | `66fdaefb57e47ff049fe4bac0718dc6cf7d97866c5f293771e0e855a60593aa2` | `7b258e6650c33b8fbc604d08d2c1896e647130e683ee790e058c750bce607855` | Channel `WEB`; Tee `STEM`; W/I `WEB` |
| CHANNEL | Interface B preview | `919e1778b78e5b169c84469c6766bdc57c44baa1c2eb425baefc347c94d2c99a` | `cf65ea1c674ff042a77290b56eb02e83d7317e92690ac531ee9c43aa81a5e568` | Channel `WEB`; Tee `STEM`; W/I `WEB` |
| CONNECTED_W | Interface A preview | `1b0eefd6f6d824e740edab2a5a6b34f8df32eb2e367ea40891d30afe5e5304f2` | `2331aa4b1ffef3d8aa0a495ffc90f0edb06b92395b129fbc86659484026d4f8b` | Connected/support W/I `WEB`; Tee `STEM` |
| CONNECTED_W | Interface B preview | `39dff7bae028874bfcfe172fd9ee4304e0d4c077279297e913afb0ff3c37f94b` | `674efe16644601186bd82a5aee27d58863af8afbc65969b57fa5b645b5f0bec7` | Connected/support W/I `WEB`; Tee `STEM` |
| RHS | Interface A preview | `f4c216fd08d594484b48093efc14f2b27d0e2d5227e82e9c4a659f0ed132f14a` | `bf983f5293ad841bfc449e7caff8ef265b47b6d55a487e65c3703d47d642bd7f` | RHS `WALL_PAIR_2`; Tee `STEM`; W/I `WEB` |
| RHS | Interface B preview | `905abc09065b207978e273669b705927fb7698eb2350bd3673eabcc1fb46bae1` | `a89104f1cd308820aa6c4b12a83456c4eb173a4e1b5e0c15d186c6b0a587d7cd` | RHS `WALL_PAIR_2`; Tee `STEM`; W/I `WEB` |
| Generic multi-row U.S. | Preview | `f21cd78fc1c332c52268295c4fb273c1dc4ae841e6d94f7edeb5cbd984558961` | `91bfb0e5dc54ce98d30f46c11e87689ed07b32524cba8c5e997205a8d36ba4c3` | W/I `WEB` |
| Generic multi-row SI | Preview | `94dee19bc2b27a9a726c94eed9e66ddcfd637d5a80a8d74230d8716b9294e9d2` | `8b2a9a73704b670f70ffcbbb07b7648bd10857e70678eb7d24483a5b265da3ff` | W/I `WEB` |
| Tee connector | Platform identity | `a572003ce54e68ffc0ac68423895eacfeabe9a1c2819e4335451c453bfcd5f72` | `79866e0ba97cc4b2beab2881650b093e5cdfb623afa91e549901756dacef51fe` | Tee `STEM` |
| Tee scaffold | Platform identity | `5719b093cd3101a7325ec2327fe3d306c5027114fc885c1e9051b81034c6367b` | `d8376c36c5bfe0245cf8536b1d4ae7b677226a731385ce58870ca66675b8e838` | Immediate parent of the corrected Tee `STEM` identity |

For every affected planar region, the exact pre-R14B canonical orientation is
`{"crosswise_axis":"Y","through_thickness_axis":"Z"}` (with `kind` also
present in the platform payload). The exact R14B orientation is
`{"crosswise_axis":"Z","crosswise_sign":-1,"through_thickness_axis":"Y"}`;
the omitted `through_thickness_sign` is the canonical positive default. All other
canonical fields compare equal. Tests retain the complete pre-R14B and post-R14B
serialized payloads in memory, recompute each hash, and inspect every topology/region
delta rather than accepting a snapshot rewrite.
