// Fixtures de FORMA tomados de respuestas reales de la API T08 (artifacts/private/t08r/samples), recortados.
// Solo sirven para pruebas de interfaz: no se presentan como resultados en ninguna pantalla.
import { BacktestDetail, BacktestItem, Page, RecoPage, Recommendation, RunDetail, RunSummary } from '../core/models';

export const realBacktest: BacktestDetail = {
 "backtest_id": "bt-hist-20260710-52b01cd999dd",
 "kind": "T07_desarrollo",
 "label": "Backtest de desarrollo T07 (4 folds solapados y simulación 01/06 a 31/07)",
 "folds": [
  "G1",
  "G2",
  "G3",
  "G4"
 ],
 "created": "2026-10-17T17:17:27Z",
 "run_id": "hist-20260710-52b01cd999dd",
 "scenario_id": "T07_simulacion_2026-06-01_2026-07-31",
 "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
 "disclaimer": "Inventario simulado con supuestos; no corresponde al inventario real de la empresa. Resultados de desarrollo sobre meses ya conocidos; no demuestran impacto en la empresa ni autorizan compras.",
 "run": {
  "run_id": "hist-20260710-52b01cd999dd",
  "run_label": "Corrida histórica de desarrollo al 10/07/2026",
  "cutoff": "2026-07-10",
  "generated_at": "2026-10-17T16:45:00Z",
  "published_at": "2026-10-17T17:17:30Z",
  "age_days_at_view": 99,
  "is_active": true
 },
 "view": "all",
 "predictive": {
  "sku": [
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "cero",
    "vista": "acum14",
    "n": 675,
    "unidades_observadas": 726.0,
    "unidades_predichas": 0.0,
    "MAE": 1.0755555555555556,
    "RMSE": 2.943920288775949,
    "WAPE": 1.0,
    "sesgo_acumulado": -726.0,
    "prop_subpronostico": 0.36592592592592593,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.6340740740740741,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.36592592592592593,
    "MAPE_ceros_excluidos": 428,
    "R2": -0.15404039075610365,
    "R2_nota": null
   },
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "promedio_28",
    "vista": "acum14",
    "n": 675,
    "unidades_observadas": 726.0,
    "unidades_predichas": 1510.3129572934504,
    "MAE": 2.023157426769557,
    "RMSE": 3.9964670466057868,
    "WAPE": 1.8810347976163238,
    "sesgo_acumulado": 784.3129572934504,
    "prop_subpronostico": 0.20296296296296296,
    "prop_sobrepronostico": 0.5748148148148148,
    "prop_exacto": 0.2222222222222222,
    "MAPE": 1.11307573544059,
    "MAPE_cobertura_reales_positivos": 0.36592592592592593,
    "MAPE_ceros_excluidos": 428,
    "R2": -1.1267742256801347,
    "R2_nota": null
   },
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "referencia_fija_0531",
    "vista": "acum14",
    "n": 675,
    "unidades_observadas": 726.0,
    "unidades_predichas": 1510.3129572934504,
    "MAE": 2.023157426769557,
    "RMSE": 3.9964670466057868,
    "WAPE": 1.8810347976163238,
    "sesgo_acumulado": 784.3129572934504,
    "prop_subpronostico": 0.20296296296296296,
    "prop_sobrepronostico": 0.5748148148148148,
    "prop_exacto": 0.2222222222222222,
    "MAPE": 1.11307573544059,
    "MAPE_cobertura_reales_positivos": 0.36592592592592593,
    "MAPE_ceros_excluidos": 428,
    "R2": -1.1267742256801347,
    "R2_nota": null
   },
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "rf_distribuido",
    "vista": "acum14",
    "n": 675,
    "unidades_observadas": 726.0,
    "unidades_predichas": 1273.1884284414439,
    "MAE": 1.7146347330124139,
    "RMSE": 3.4687761232674106,
    "WAPE": 1.5941851856520377,
    "sesgo_acumulado": 547.1884284414439,
    "prop_subpronostico": 0.2088888888888889,
    "prop_sobrepronostico": 0.5688888888888889,
    "prop_exacto": 0.2222222222222222,
    "MAPE": 1.0142451748887193,
    "MAPE_cobertura_reales_positivos": 0.36592592592592593,
    "MAPE_ceros_excluidos": 428,
    "R2": -0.602217452873983,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "cero",
    "vista": "acum10",
    "n": 3250,
    "unidades_observadas": 7467.0,
    "unidades_predichas": 0.0,
    "MAE": 2.2975384615384615,
    "RMSE": 7.849566377048627,
    "WAPE": 1.0,
    "sesgo_acumulado": -7467.0,
    "prop_subpronostico": 0.43815384615384617,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.5618461538461539,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.43815384615384617,
    "MAPE_ceros_excluidos": 1826,
    "R2": -0.09369831741963774,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "cero",
    "vista": "acum14",
    "n": 3250,
    "unidades_observadas": 10594.0,
    "unidades_predichas": 0.0,
    "MAE": 3.259692307692308,
    "RMSE": 9.88524930622156,
    "WAPE": 1.0,
    "sesgo_acumulado": -10594.0,
    "prop_subpronostico": 0.5058461538461538,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.49415384615384617,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.5058461538461538,
    "MAPE_ceros_excluidos": 1606,
    "R2": -0.12200346335414913,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "promedio_28",
    "vista": "acum10",
    "n": 3250,
    "unidades_observadas": 7467.0,
    "unidades_predichas": 6627.857142857143,
    "MAE": 1.8671648351648351,
    "RMSE": 6.288373064058672,
    "WAPE": 0.8126805563527137,
    "sesgo_acumulado": -839.1428571428569,
    "prop_subpronostico": 0.28923076923076924,
    "prop_sobrepronostico": 0.40307692307692305,
    "prop_exacto": 0.3076923076923077,
    "MAPE": 0.8526285399458002,
    "MAPE_cobertura_reales_positivos": 0.43815384615384617,
    "MAPE_ceros_excluidos": 1826,
    "R2": 0.2980877709651629,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "promedio_28",
    "vista": "acum14",
    "n": 3250,
    "unidades_observadas": 10594.0,
    "unidades_predichas": 9279.0,
    "MAE": 2.4833846153846153,
    "RMSE": 7.760570954411894,
    "WAPE": 0.7618463281102511,
    "sesgo_acumulado": -1315.0,
    "prop_subpronostico": 0.34276923076923077,
    "prop_sobrepronostico": 0.36,
    "prop_exacto": 0.29723076923076924,
    "MAPE": 0.8904652796753556,
    "MAPE_cobertura_reales_positivos": 0.5058461538461538,
    "MAPE_ceros_excluidos": 1606,
    "R2": 0.3084775369568753,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "referencia_fija_0531",
    "vista": "acum10",
    "n": 3250,
    "unidades_observadas": 7467.0,
    "unidades_predichas": 9147.258690647532,
    "MAE": 2.4990017828936972,
    "RMSE": 9.986332115651104,
    "WAPE": 1.087686593599105,
    "sesgo_acumulado": 1680.2586906475317,
    "prop_subpronostico": 0.2784615384615385,
    "prop_sobrepronostico": 0.4793846153846154,
    "prop_exacto": 0.24215384615384616,
    "MAPE": 1.0047498798429328,
    "MAPE_cobertura_reales_positivos": 0.43815384615384617,
    "MAPE_ceros_excluidos": 1826,
    "R2": -0.7701832297839868,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "referencia_fija_0531",
    "vista": "acum14",
    "n": 3250,
    "unidades_observadas": 10594.0,
    "unidades_predichas": 12806.162166906544,
    "MAE": 3.294137551363757,
    "RMSE": 13.189331855228088,
    "WAPE": 1.010567023025506,
    "sesgo_acumulado": 2212.1621669065444,
    "prop_subpronostico": 0.31446153846153846,
    "prop_sobrepronostico": 0.4461538461538462,
    "prop_exacto": 0.2393846153846154,
    "MAPE": 1.0419567669797523,
    "MAPE_cobertura_reales_positivos": 0.5058461538461538,
    "MAPE_ceros_excluidos": 1606,
    "R2": -0.9973976534440732,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "rf_distribuido",
    "vista": "acum10",
    "n": 3250,
    "unidades_observadas": 7467.0,
    "unidades_predichas": 6839.999896346267,
    "MAE": 1.8911614986106595,
    "RMSE": 6.302678972131252,
    "WAPE": 0.8231250663565881,
    "sesgo_acumulado": -627.0001036537333,
    "prop_subpronostico": 0.2876923076923077,
    "prop_sobrepronostico": 0.40584615384615386,
    "prop_exacto": 0.30646153846153845,
    "MAPE": 0.8784485142404783,
    "MAPE_cobertura_reales_positivos": 0.43815384615384617,
    "MAPE_ceros_excluidos": 1826,
    "R2": 0.29489046895847915,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "rf_distribuido",
    "vista": "acum14",
    "n": 3250,
    "unidades_observadas": 10594.0,
    "unidades_predichas": 9491.347121557503,
    "MAE": 2.521037505123541,
    "RMSE": 7.808122791929426,
    "WAPE": 0.7733973845244013,
    "sesgo_acumulado": -1102.6528784424972,
    "prop_subpronostico": 0.32276923076923075,
    "prop_sobrepronostico": 0.3883076923076923,
    "prop_exacto": 0.28892307692307695,
    "MAPE": 0.917643768023403,
    "MAPE_cobertura_reales_positivos": 0.5058461538461538,
    "MAPE_ceros_excluidos": 1606,
    "R2": 0.299977155337699,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "cero",
    "vista": "acum10",
    "n": 11957,
    "unidades_observadas": 26676.0,
    "unidades_predichas": 0.0,
    "MAE": 2.2309943965877728,
    "RMSE": 6.909128323760955,
    "WAPE": 1.0,
    "sesgo_acumulado": -26676.0,
    "prop_subpronostico": 0.4460985196955758,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.5539014803044242,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.4460985196955758,
    "MAPE_ceros_excluidos": 6623,
    "R2": -0.11640517320285348,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "cero",
    "vista": "acum14",
    "n": 11957,
    "unidades_observadas": 37791.0,
    "unidades_predichas": 0.0,
    "MAE": 3.1605753951660116,
    "RMSE": 9.325217900144311,
    "WAPE": 1.0,
    "sesgo_acumulado": -37791.0,
    "prop_subpronostico": 0.517688383373756,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.48231161662624406,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.517688383373756,
    "MAPE_ceros_excluidos": 5767,
    "R2": -0.12978015019552758,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "promedio_28",
    "vista": "acum10",
    "n": 11957,
    "unidades_observadas": 26676.0,
    "unidades_predichas": 28306.903439153437,
    "MAE": 2.0737161999811495,
    "RMSE": 6.749762691115942,
    "WAPE": 0.9295030965352603,
    "sesgo_acumulado": 1630.903439153437,
    "prop_subpronostico": 0.2880321150790332,
    "prop_sobrepronostico": 0.4264447603914025,
    "prop_exacto": 0.2855231245295643,
    "MAPE": 0.9023786217164776,
    "MAPE_cobertura_reales_positivos": 0.4460985196955758,
    "MAPE_ceros_excluidos": 6623,
    "R2": -0.06549724378815114,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "promedio_28",
    "vista": "acum14",
    "n": 11957,
    "unidades_observadas": 37791.0,
    "unidades_predichas": 39963.56481481482,
    "MAE": 2.7578252184967917,
    "RMSE": 9.29062118182576,
    "WAPE": 0.8725706156906707,
    "sesgo_acumulado": 2172.5648148148175,
    "prop_subpronostico": 0.31579827715982267,
    "prop_sobrepronostico": 0.41297984444258595,
    "prop_exacto": 0.2712218783975914,
    "MAPE": 1.003143244603552,
    "MAPE_cobertura_reales_positivos": 0.517688383373756,
    "MAPE_ceros_excluidos": 5767,
    "R2": -0.12141269328481008,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "referencia_fija_0531",
    "vista": "acum10",
    "n": 11957,
    "unidades_observadas": 26676.0,
    "unidades_predichas": 34127.15154779039,
    "MAE": 2.4569474015320565,
    "RMSE": 9.369560548286444,
    "WAPE": 1.1012790553350877,
    "sesgo_acumulado": 7451.151547790389,
    "prop_subpronostico": 0.27523626327674167,
    "prop_sobrepronostico": 0.47319561762984025,
    "prop_exacto": 0.2515681190934181,
    "MAPE": 1.0004712798200814,
    "MAPE_cobertura_reales_positivos": 0.4460985196955758,
    "MAPE_ceros_excluidos": 6623,
    "R2": -1.0531173190081087,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "referencia_fija_0531",
    "vista": "acum14",
    "n": 11957,
    "unidades_observadas": 37791.0,
    "unidades_predichas": 48111.91216690654,
    "MAE": 3.2695836186038716,
    "RMSE": 12.828855979734442,
    "WAPE": 1.034489993057778,
    "sesgo_acumulado": 10320.912166906543,
    "prop_subpronostico": 0.30969306682278164,
    "prop_sobrepronostico": 0.44676758384210086,
    "prop_exacto": 0.2435393493351175,
    "MAPE": 1.1107471726953186,
    "MAPE_cobertura_reales_positivos": 0.517688383373756,
    "MAPE_ceros_excluidos": 5767,
    "R2": -1.138217216493063,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "rf_distribuido",
    "vista": "acum10",
    "n": 11957,
    "unidades_observadas": 26676.0,
    "unidades_predichas": 32240.130498297465,
    "MAE": 2.2459089773526135,
    "RMSE": 7.793570895869646,
    "WAPE": 1.0066851717725747,
    "sesgo_acumulado": 5564.130498297465,
    "prop_subpronostico": 0.2680438237015974,
    "prop_sobrepronostico": 0.44835661119009784,
    "prop_exacto": 0.28359956510830475,
    "MAPE": 0.9956927713649749,
    "MAPE_cobertura_reales_positivos": 0.4460985196955758,
    "MAPE_ceros_excluidos": 6623,
    "R2": -0.42052310898764556,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "rf_distribuido",
    "vista": "acum14",
    "n": 11957,
    "unidades_observadas": 37791.0,
    "unidades_predichas": 44117.457367003335,
    "MAE": 2.9368338915413683,
    "RMSE": 10.539633649346948,
    "WAPE": 0.9292086168971485,
    "sesgo_acumulado": 6326.457367003335,
    "prop_subpronostico": 0.2980680772769089,
    "prop_sobrepronostico": 0.4344735301497031,
    "prop_exacto": 0.267458392573388,
    "MAPE": 1.0933169486312204,
    "MAPE_cobertura_reales_positivos": 0.517688383373756,
    "MAPE_ceros_excluidos": 5767,
    "R2": -0.44320157273727667,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "historia_corta",
    "metodo": "cero",
    "vista": "acum14",
    "n": 2036,
    "unidades_observadas": 3885.0,
    "unidades_predichas": 0.0,
    "MAE": 1.9081532416502947,
    "RMSE": 8.376134354167021,
    "WAPE": 1.0,
    "sesgo_acumulado": -3885.0,
    "prop_subpronostico": 0.36787819253438114,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.6321218074656189,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.36787819253438114,
    "MAPE_ceros_excluidos": 1287,
    "R2": -0.05473732162016365,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "historia_corta",
    "metodo": "promedio_28",
    "vista": "acum14",
    "n": 2036,
    "unidades_observadas": 3885.0,
    "unidades_predichas": 6505.625396746431,
    "MAE": 2.6709320497910505,
    "RMSE": 6.593272555158446,
    "WAPE": 1.3997471437257603,
    "sesgo_acumulado": 2620.625396746431,
    "prop_subpronostico": 0.19646365422396855,
    "prop_sobrepronostico": 0.5854616895874263,
    "prop_exacto": 0.2180746561886051,
    "MAPE": 1.1746534178328438,
    "MAPE_cobertura_reales_positivos": 0.36787819253438114,
    "MAPE_ceros_excluidos": 1287,
    "R2": 0.34647967015569114,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "historia_corta",
    "metodo": "referencia_fija_0531",
    "vista": "acum14",
    "n": 1431,
    "unidades_observadas": 1687.0,
    "unidades_predichas": 4189.123421642669,
    "MAE": 2.658675594553736,
    "RMSE": 5.14535160501577,
    "WAPE": 2.255225119031652,
    "sesgo_acumulado": 2502.123421642669,
    "prop_subpronostico": 0.17540181691125087,
    "prop_sobrepronostico": 0.6792452830188679,
    "prop_exacto": 0.1453529000698812,
    "MAPE": 1.3674169100862277,
    "MAPE_cobertura_reales_positivos": 0.3417190775681342,
    "MAPE_ceros_excluidos": 942,
    "R2": -1.0866265403136781,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "historia_corta",
    "metodo": "rf_distribuido",
    "vista": "acum14",
    "n": 2036,
    "unidades_observadas": 3885.0,
    "unidades_predichas": 4196.954518430092,
    "MAE": 2.020964267666643,
    "RMSE": 5.632854362923509,
    "WAPE": 1.0591205274052213,
    "sesgo_acumulado": 311.9545184300923,
    "prop_subpronostico": 0.2387033398821218,
    "prop_sobrepronostico": 0.5451866404715128,
    "prop_exacto": 0.21611001964636542,
    "MAPE": 0.913285608968306,
    "MAPE_cobertura_reales_positivos": 0.36787819253438114,
    "MAPE_ceros_excluidos": 1287,
    "R2": 0.523004711413511,
    "R2_nota": null
   }
  ],
  "categoria": [
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "cero",
    "vista": "acum14",
    "n": 0
   },
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "promedio_28",
    "vista": "acum14",
    "n": 0
   },
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "rf_categoria",
    "vista": "acum14",
    "n": 0
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "cero",
    "vista": "acum10",
    "n": 36,
    "unidades_observadas": 8289.0,
    "unidades_predichas": 0.0,
    "MAE": 230.25,
    "RMSE": 603.4571926270606,
    "WAPE": 1.0,
    "sesgo_acumulado": -8289.0,
    "prop_subpronostico": 0.8611111111111112,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.1388888888888889,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.8611111111111112,
    "MAPE_ceros_excluidos": 5,
    "R2": -0.17038671280888473,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "cero",
    "vista": "acum14",
    "n": 36,
    "unidades_observadas": 11769.0,
    "unidades_predichas": 0.0,
    "MAE": 326.9166666666667,
    "RMSE": 866.5121496872133,
    "WAPE": 1.0,
    "sesgo_acumulado": -11769.0,
    "prop_subpronostico": 0.8888888888888888,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.1111111111111111,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.8888888888888888,
    "MAPE_ceros_excluidos": 4,
    "R2": -0.16596224409466354,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "promedio_28",
    "vista": "acum10",
    "n": 36,
    "unidades_observadas": 8289.0,
    "unidades_predichas": 7362.500000000001,
    "MAE": 35.64087301587299,
    "RMSE": 82.70002635676974,
    "WAPE": 0.1547920652155179,
    "sesgo_acumulado": -926.4999999999991,
    "prop_subpronostico": 0.5277777777777778,
    "prop_sobrepronostico": 0.4444444444444444,
    "prop_exacto": 0.027777777777777776,
    "MAPE": 0.8621430712288166,
    "MAPE_cobertura_reales_positivos": 0.8611111111111112,
    "MAPE_ceros_excluidos": 5,
    "R2": 0.9780189850038885,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "promedio_28",
    "vista": "acum14",
    "n": 36,
    "unidades_observadas": 11769.0,
    "unidades_predichas": 10307.500000000002,
    "MAE": 53.29166666666662,
    "RMSE": 137.7389086077147,
    "WAPE": 0.16301300025490684,
    "sesgo_acumulado": -1461.4999999999982,
    "prop_subpronostico": 0.5833333333333334,
    "prop_sobrepronostico": 0.4166666666666667,
    "prop_exacto": 0.0,
    "MAPE": 0.7434757394692996,
    "MAPE_cobertura_reales_positivos": 0.8888888888888888,
    "MAPE_ceros_excluidos": 4,
    "R2": 0.9705389345176932,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "rf_categoria",
    "vista": "acum10",
    "n": 36,
    "unidades_observadas": 8289.0,
    "unidades_predichas": 7611.405829270154,
    "MAE": 30.42942506782119,
    "RMSE": 56.12906694270951,
    "WAPE": 0.13215819790584665,
    "sesgo_acumulado": -677.5941707298462,
    "prop_subpronostico": 0.5,
    "prop_sobrepronostico": 0.5,
    "prop_exacto": 0.0,
    "MAPE": 1.1098162407860508,
    "MAPE_cobertura_reales_positivos": 0.8611111111111112,
    "MAPE_ceros_excluidos": 5,
    "R2": 0.9898746022522795,
    "R2_nota": null
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "rf_categoria",
    "vista": "acum14",
    "n": 36,
    "unidades_observadas": 11769.0,
    "unidades_predichas": 10565.734562204849,
    "MAE": 48.25119198296571,
    "RMSE": 99.74566082379316,
    "WAPE": 0.14759477537486324,
    "sesgo_acumulado": -1203.2654377951512,
    "prop_subpronostico": 0.5833333333333334,
    "prop_sobrepronostico": 0.4166666666666667,
    "prop_exacto": 0.0,
    "MAPE": 0.9322999601773582,
    "MAPE_cobertura_reales_positivos": 0.8888888888888888,
    "MAPE_ceros_excluidos": 4,
    "R2": 0.9845501880298654,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "cero",
    "vista": "acum10",
    "n": 144,
    "unidades_observadas": 29422.0,
    "unidades_predichas": 0.0,
    "MAE": 204.31944444444446,
    "RMSE": 524.8792321413882,
    "WAPE": 1.0,
    "sesgo_acumulado": -29422.0,
    "prop_subpronostico": 0.875,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.125,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.875,
    "MAPE_ceros_excluidos": 18,
    "R2": -0.17859302135038368,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "cero",
    "vista": "acum14",
    "n": 144,
    "unidades_observadas": 41676.0,
    "unidades_predichas": 0.0,
    "MAE": 289.4166666666667,
    "RMSE": 746.5719899052677,
    "WAPE": 1.0,
    "sesgo_acumulado": -41676.0,
    "prop_subpronostico": 0.8888888888888888,
    "prop_sobrepronostico": 0.0,
    "prop_exacto": 0.1111111111111111,
    "MAPE": 1.0,
    "MAPE_cobertura_reales_positivos": 0.8888888888888888,
    "MAPE_ceros_excluidos": 16,
    "R2": -0.1768594593923274,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "promedio_28",
    "vista": "acum10",
    "n": 144,
    "unidades_observadas": 29422.0,
    "unidades_predichas": 30982.48015873016,
    "MAE": 44.34243643445032,
    "RMSE": 103.64832449630735,
    "WAPE": 0.21702504406773318,
    "sesgo_acumulado": 1560.480158730159,
    "prop_subpronostico": 0.4027777777777778,
    "prop_sobrepronostico": 0.5208333333333334,
    "prop_exacto": 0.0763888888888889,
    "MAPE": 0.6125755815547621,
    "MAPE_cobertura_reales_positivos": 0.875,
    "MAPE_ceros_excluidos": 18,
    "R2": 0.9540410965227262,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "promedio_28",
    "vista": "acum14",
    "n": 144,
    "unidades_observadas": 41676.0,
    "unidades_predichas": 43742.829365079364,
    "MAE": 58.41854975014697,
    "RMSE": 151.05745679314018,
    "WAPE": 0.20184929369472032,
    "sesgo_acumulado": 2066.829365079364,
    "prop_subpronostico": 0.4236111111111111,
    "prop_sobrepronostico": 0.5138888888888888,
    "prop_exacto": 0.0625,
    "MAPE": 0.4727099527807437,
    "MAPE_cobertura_reales_positivos": 0.8888888888888888,
    "MAPE_ceros_excluidos": 16,
    "R2": 0.9518201375366883,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "rf_categoria",
    "vista": "acum10",
    "n": 144,
    "unidades_observadas": 29422.0,
    "unidades_predichas": 35305.383390792,
    "MAE": 58.84672515297339,
    "RMSE": 158.4370353204451,
    "WAPE": 0.28801333770743553,
    "sesgo_acumulado": 5883.383390791998,
    "prop_subpronostico": 0.2916666666666667,
    "prop_sobrepronostico": 0.7083333333333334,
    "prop_exacto": 0.0,
    "MAPE": 0.8503504219895561,
    "MAPE_cobertura_reales_positivos": 0.875,
    "MAPE_ceros_excluidos": 18,
    "R2": 0.8926113207879799,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "primaria",
    "metodo": "rf_categoria",
    "vista": "acum14",
    "n": 144,
    "unidades_observadas": 41676.0,
    "unidades_predichas": 48314.41188543342,
    "MAE": 73.75245653126113,
    "RMSE": 201.06752539289548,
    "WAPE": 0.25483140753675027,
    "sesgo_acumulado": 6638.411885433423,
    "prop_subpronostico": 0.3263888888888889,
    "prop_sobrepronostico": 0.6736111111111112,
    "prop_exacto": 0.0,
    "MAPE": 0.6595883492153747,
    "MAPE_cobertura_reales_positivos": 0.8888888888888888,
    "MAPE_ceros_excluidos": 16,
    "R2": 0.9146379012041088,
    "R2_nota": null
   },
   {
    "fold": "AGREGADO",
    "cohorte": "historia_corta",
    "metodo": "cero",
    "vista": "acum14",
    "n": 0
   },
   {
    "fold": "AGREGADO",
    "cohorte": "historia_corta",
    "metodo": "promedio_28",
    "vista": "acum14",
    "n": 0
   },
   {
    "fold": "AGREGADO",
    "cohorte": "historia_corta",
    "metodo": "rf_categoria",
    "vista": "acum14",
    "n": 0
   }
  ],
  "nota": "La fila fold=AGREGADO suma bloques de origen distinto y solapados; no son unidades únicas ni admite pruebas de significación."
 },
 "selection": {
  "vista": "acum14",
  "WAPE_candidato": 0.9292086168971485,
  "WAPE_comparador": 0.8725706156906707,
  "mejora_relativa": -0.06490936113135873,
  "folds_favorables": [],
  "sesgo_relativo": 0.16740645569059656,
  "cumple_regla": false,
  "nota": "no cumple la regla provisional",
  "metodo_elegido": "promedio_28",
  "comparador": "rf_categoria_distribuido",
  "control": "cero"
 },
 "coverage": {
  "sku": [
   {
    "fold": "G1",
    "cohorte": "primaria",
    "metodo": "universo_comun",
    "entidades": 2672,
    "comunes": 2672,
    "dias_evaluables_21": 20
   },
   {
    "fold": "G1",
    "cohorte": "primaria",
    "metodo": "referencia_fija_0531",
    "entidades_con_prediccion": 2672,
    "comunes": 2672
   },
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "universo_comun",
    "entidades": 675,
    "comunes": 675,
    "dias_evaluables_21": 20
   },
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "referencia_fija_0531",
    "entidades_con_prediccion": 675,
    "comunes": 675
   },
   {
    "fold": "G2",
    "cohorte": "primaria",
    "metodo": "universo_comun",
    "entidades": 2914,
    "comunes": 2914,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G2",
    "cohorte": "primaria",
    "metodo": "referencia_fija_0531",
    "entidades_con_prediccion": 2914,
    "comunes": 2914
   },
   {
    "fold": "G2",
    "cohorte": "historia_corta",
    "metodo": "universo_comun",
    "entidades": 536,
    "comunes": 536,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G2",
    "cohorte": "historia_corta",
    "metodo": "referencia_fija_0531",
    "entidades_con_prediccion": 433,
    "comunes": 536
   },
   {
    "fold": "G3",
    "cohorte": "primaria",
    "metodo": "universo_comun",
    "entidades": 3121,
    "comunes": 3121,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G3",
    "cohorte": "primaria",
    "metodo": "referencia_fija_0531",
    "entidades_con_prediccion": 3121,
    "comunes": 3121
   },
   {
    "fold": "G3",
    "cohorte": "historia_corta",
    "metodo": "universo_comun",
    "entidades": 428,
    "comunes": 428,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G3",
    "cohorte": "historia_corta",
    "metodo": "referencia_fija_0531",
    "entidades_con_prediccion": 226,
    "comunes": 428
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "universo_comun",
    "entidades": 3250,
    "comunes": 3250,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "referencia_fija_0531",
    "entidades_con_prediccion": 3250,
    "comunes": 3250
   },
   {
    "fold": "G4",
    "cohorte": "historia_corta",
    "metodo": "universo_comun",
    "entidades": 397,
    "comunes": 397,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G4",
    "cohorte": "historia_corta",
    "metodo": "referencia_fija_0531",
    "entidades_con_prediccion": 97,
    "comunes": 397
   }
  ],
  "categoria": [
   {
    "fold": "G1",
    "cohorte": "primaria",
    "metodo": "universo_comun",
    "entidades": 36,
    "comunes": 36,
    "dias_evaluables_21": 20
   },
   {
    "fold": "G1",
    "cohorte": "historia_corta",
    "metodo": "universo_comun",
    "entidades": 0,
    "comunes": 0,
    "dias_evaluables_21": 20
   },
   {
    "fold": "G2",
    "cohorte": "primaria",
    "metodo": "universo_comun",
    "entidades": 36,
    "comunes": 36,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G2",
    "cohorte": "historia_corta",
    "metodo": "universo_comun",
    "entidades": 0,
    "comunes": 0,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G3",
    "cohorte": "primaria",
    "metodo": "universo_comun",
    "entidades": 36,
    "comunes": 36,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G3",
    "cohorte": "historia_corta",
    "metodo": "universo_comun",
    "entidades": 0,
    "comunes": 0,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G4",
    "cohorte": "primaria",
    "metodo": "universo_comun",
    "entidades": 36,
    "comunes": 36,
    "dias_evaluables_21": 21
   },
   {
    "fold": "G4",
    "cohorte": "historia_corta",
    "metodo": "universo_comun",
    "entidades": 0,
    "comunes": 0,
    "dias_evaluables_21": 21
   }
  ]
 },
 "simulation": [
  {
   "scenario_id": "T07_L3_S0_R7_2026-06-01_2026-07-31",
   "L": 3,
   "S": 0,
   "R": 7,
   "policy": "referencia_fija",
   "total": {
    "skus": 3347,
    "dias_sku_evaluables": 200820,
    "demanda_proxy_elegible_unidades": 42679.0,
    "atendidas_unidades": 28514.0,
    "perdidas_unidades": 14165.0,
    "fill_rate": 0.6681037512594016,
    "dias_sku_con_faltante": 5719,
    "tasa_dias_sku_con_faltante": 0.028478239219201274,
    "tasa_faltante_sobre_dias_con_demanda": 0.2912507639030352,
    "stock_medio_unidades_por_dia": 8091.704918032787,
    "stock_inicial_unidades": 10738.0,
    "stock_final_unidades": 9154.0,
    "pedidos_lineas": 8696,
    "pedidos_unidades": 26930.0,
    "recibidas_unidades": 26930.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 3320.5423380821926,
    "compras_desembolsadas_supuesto": 321543.72250000003,
    "costo_consumido_supuesto": 342208.685,
    "valor_stock_inicial_supuesto": 130855.075,
    "valor_stock_final_supuesto": 110190.1125,
    "valor_transito_final_supuesto": 0.0
   },
   "primaria": {
    "skus": 2672,
    "dias_sku_evaluables": 160320,
    "demanda_proxy_elegible_unidades": 39124.0,
    "atendidas_unidades": 26452.0,
    "perdidas_unidades": 12672.0,
    "fill_rate": 0.6761067375523975,
    "dias_sku_con_faltante": 5088,
    "tasa_dias_sku_con_faltante": 0.03173652694610778,
    "tasa_faltante_sobre_dias_con_demanda": 0.28645422812746313,
    "stock_medio_unidades_por_dia": 6888.540983606557,
    "stock_inicial_unidades": 9341.0,
    "stock_final_unidades": 7857.0,
    "pedidos_lineas": 7681,
    "pedidos_unidades": 24968.0,
    "recibidas_unidades": 24968.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 2569.3531482191784,
    "compras_desembolsadas_supuesto": 291105.69800000003,
    "costo_consumido_supuesto": 309903.0155,
    "valor_stock_inicial_supuesto": 105360.4565,
    "valor_stock_final_supuesto": 86563.139,
    "valor_transito_final_supuesto": 0.0
   },
   "historia_corta": {
    "skus": 675,
    "dias_sku_evaluables": 40500,
    "demanda_proxy_elegible_unidades": 3555.0,
    "atendidas_unidades": 2062.0,
    "perdidas_unidades": 1493.0,
    "fill_rate": 0.580028129395218,
    "dias_sku_con_faltante": 631,
    "tasa_dias_sku_con_faltante": 0.015580246913580247,
    "tasa_faltante_sobre_dias_con_demanda": 0.33671291355389543,
    "stock_medio_unidades_por_dia": 1203.1639344262296,
    "stock_inicial_unidades": 1397.0,
    "stock_final_unidades": 1297.0,
    "pedidos_lineas": 1015,
    "pedidos_unidades": 1962.0,
    "recibidas_unidades": 1962.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 751.1891898630138,
    "compras_desembolsadas_supuesto": 30438.0245,
    "costo_consumido_supuesto": 32305.6695,
    "valor_stock_inicial_supuesto": 25494.618499999997,
    "valor_stock_final_supuesto": 23626.9735,
    "valor_transito_final_supuesto": 0.0
   },
   "identidad_valor": 4.3655745685100555e-11,
   "conservacion": {
    "saldo_por_sku_ok": true,
    "demanda_ok": true,
    "pedidos_ok": true,
    "sistema": 0
   },
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "unit": "unidad base",
   "currency": "PEN"
  },
  {
   "scenario_id": "T07_L3_S0_R7_2026-06-01_2026-07-31",
   "L": 3,
   "S": 0,
   "R": 7,
   "policy": "promedio_28",
   "total": {
    "skus": 3347,
    "dias_sku_evaluables": 200820,
    "demanda_proxy_elegible_unidades": 42679.0,
    "atendidas_unidades": 30218.0,
    "perdidas_unidades": 12461.0,
    "fill_rate": 0.7080297101619063,
    "dias_sku_con_faltante": 4775,
    "tasa_dias_sku_con_faltante": 0.023777512199980082,
    "tasa_faltante_sobre_dias_con_demanda": 0.24317579955184354,
    "stock_medio_unidades_por_dia": 8520.131147540984,
    "stock_inicial_unidades": 10738.0,
    "stock_final_unidades": 10213.0,
    "pedidos_lineas": 8163,
    "pedidos_unidades": 29693.0,
    "recibidas_unidades": 29693.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 3645.00249260274,
    "compras_desembolsadas_supuesto": 361819.6985,
    "costo_consumido_supuesto": 361817.248,
    "valor_stock_inicial_supuesto": 130855.075,
    "valor_stock_final_supuesto": 130857.52550000002,
    "valor_transito_final_supuesto": 0.0
   },
   "primaria": {
    "skus": 2672,
    "dias_sku_evaluables": 160320,
    "demanda_proxy_elegible_unidades": 39124.0,
    "atendidas_unidades": 27853.0,
    "perdidas_unidades": 11271.0,
    "fill_rate": 0.7119159595133422,
    "dias_sku_con_faltante": 4280,
    "tasa_dias_sku_con_faltante": 0.026696606786427147,
    "tasa_faltante_sobre_dias_con_demanda": 0.24096385542168675,
    "stock_medio_unidades_por_dia": 7266.3442622950815,
    "stock_inicial_unidades": 9341.0,
    "stock_final_unidades": 8759.0,
    "pedidos_lineas": 7199,
    "pedidos_unidades": 27271.0,
    "recibidas_unidades": 27271.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 2802.1848649315075,
    "compras_desembolsadas_supuesto": 322967.827,
    "costo_consumido_supuesto": 325333.82050000003,
    "valor_stock_inicial_supuesto": 105360.4565,
    "valor_stock_final_supuesto": 102994.46300000002,
    "valor_transito_final_supuesto": 0.0
   },
   "historia_corta": {
    "skus": 675,
    "dias_sku_evaluables": 40500,
    "demanda_proxy_elegible_unidades": 3555.0,
    "atendidas_unidades": 2365.0,
    "perdidas_unidades": 1190.0,
    "fill_rate": 0.6652601969057665,
    "dias_sku_con_faltante": 495,
    "tasa_dias_sku_con_faltante": 0.012222222222222223,
    "tasa_faltante_sobre_dias_con_demanda": 0.2641408751334045,
    "stock_medio_unidades_por_dia": 1253.7868852459017,
    "stock_inicial_unidades": 1397.0,
    "stock_final_unidades": 1454.0,
    "pedidos_lineas": 964,
    "pedidos_unidades": 2422.0,
    "recibidas_unidades": 2422.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 842.8176276712329,
    "compras_desembolsadas_supuesto": 38851.8715,
    "costo_consumido_supuesto": 36483.427500000005,
    "valor_stock_inicial_supuesto": 25494.618499999997,
    "valor_stock_final_supuesto": 27863.0625,
    "valor_transito_final_supuesto": 0.0
   },
   "identidad_valor": -2.9103830456733704e-11,
   "conservacion": {
    "saldo_por_sku_ok": true,
    "demanda_ok": true,
    "pedidos_ok": true,
    "sistema": 0
   },
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "unit": "unidad base",
   "currency": "PEN"
  },
  {
   "scenario_id": "T07_L3_S0_R7_2026-06-01_2026-07-31",
   "L": 3,
   "S": 0,
   "R": 7,
   "policy": "rf_categoria_distribuido",
   "total": {
    "skus": 3347,
    "dias_sku_evaluables": 200820,
    "demanda_proxy_elegible_unidades": 42679.0,
    "atendidas_unidades": 30932.0,
    "perdidas_unidades": 11747.0,
    "fill_rate": 0.7247592492795052,
    "dias_sku_con_faltante": 4493,
    "tasa_dias_sku_con_faltante": 0.022373269594661887,
    "tasa_faltante_sobre_dias_con_demanda": 0.22881442248930536,
    "stock_medio_unidades_por_dia": 9460.426229508197,
    "stock_inicial_unidades": 10738.0,
    "stock_final_unidades": 10989.0,
    "pedidos_lineas": 8473,
    "pedidos_unidades": 31183.0,
    "recibidas_unidades": 31183.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 3950.9325254794526,
    "compras_desembolsadas_supuesto": 379244.866,
    "costo_consumido_supuesto": 370416.5985,
    "valor_stock_inicial_supuesto": 130855.075,
    "valor_stock_final_supuesto": 139683.3425,
    "valor_transito_final_supuesto": 0.0
   },
   "primaria": {
    "skus": 2672,
    "dias_sku_evaluables": 160320,
    "demanda_proxy_elegible_unidades": 39124.0,
    "atendidas_unidades": 28522.0,
    "perdidas_unidades": 10602.0,
    "fill_rate": 0.7290154380942644,
    "dias_sku_con_faltante": 4018,
    "tasa_dias_sku_con_faltante": 0.025062375249500998,
    "tasa_faltante_sobre_dias_con_demanda": 0.22621326427204144,
    "stock_medio_unidades_por_dia": 8148.163934426229,
    "stock_inicial_unidades": 9341.0,
    "stock_final_unidades": 9464.0,
    "pedidos_lineas": 7462,
    "pedidos_unidades": 28645.0,
    "recibidas_unidades": 28645.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 3093.5958816438365,
    "compras_desembolsadas_supuesto": 339683.00600000005,
    "costo_consumido_supuesto": 333492.82200000004,
    "valor_stock_inicial_supuesto": 105360.4565,
    "valor_stock_final_supuesto": 111550.64050000001,
    "valor_transito_final_supuesto": 0.0
   },
   "historia_corta": {
    "skus": 675,
    "dias_sku_evaluables": 40500,
    "demanda_proxy_elegible_unidades": 3555.0,
    "atendidas_unidades": 2410.0,
    "perdidas_unidades": 1145.0,
    "fill_rate": 0.6779184247538678,
    "dias_sku_con_faltante": 475,
    "tasa_dias_sku_con_faltante": 0.011728395061728396,
    "tasa_faltante_sobre_dias_con_demanda": 0.2534685165421558,
    "stock_medio_unidades_por_dia": 1312.2622950819673,
    "stock_inicial_unidades": 1397.0,
    "stock_final_unidades": 1525.0,
    "pedidos_lineas": 1011,
    "pedidos_unidades": 2538.0,
    "recibidas_unidades": 2538.0,
    "transito_final_unidades": 0.0,
    "holding_supuesto": 857.3366438356165,
    "compras_desembolsadas_supuesto": 39561.86,
    "costo_consumido_supuesto": 36923.7765,
    "valor_stock_inicial_supuesto": 25494.618499999997,
    "valor_stock_final_supuesto": 28132.701999999997,
    "valor_transito_final_supuesto": 0.0
   },
   "identidad_valor": -2.9103830456733704e-11,
   "conservacion": {
    "saldo_por_sku_ok": true,
    "demanda_ok": true,
    "pedidos_ok": true,
    "sistema": 0
   },
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "unit": "unidad base",
   "currency": "PEN"
  },
  {
   "scenario_id": "T07_L7_S7_R7_2026-06-01_2026-07-31",
   "L": 7,
   "S": 7,
   "R": 7,
   "policy": "referencia_fija",
   "total": {
    "skus": 3347,
    "dias_sku_evaluables": 200820,
    "demanda_proxy_elegible_unidades": 42679.0,
    "atendidas_unidades": 31625.0,
    "perdidas_unidades": 11054.0,
    "fill_rate": 0.7409967431289393,
    "dias_sku_con_faltante": 4514,
    "tasa_dias_sku_con_faltante": 0.02247784085250473,
    "tasa_faltante_sobre_dias_con_demanda": 0.2298838867386433,
    "stock_medio_unidades_por_dia": 15283.442622950819,
    "stock_inicial_unidades": 13992.0,
    "stock_final_unidades": 15182.0,
    "pedidos_lineas": 10186,
    "pedidos_unidades": 36813.0,
    "recibidas_unidades": 32815.0,
    "transito_final_unidades": 3998.0,
    "holding_supuesto": 6032.625570684933,
    "compras_desembolsadas_supuesto": 430951.5665,
    "costo_consumido_supuesto": 373722.622,
    "valor_stock_inicial_supuesto": 166565.477,
    "valor_stock_final_supuesto": 174538.44199999998,
    "valor_transito_final_supuesto": 49255.9795
   },
   "primaria": {
    "skus": 2672,
    "dias_sku_evaluables": 160320,
    "demanda_proxy_elegible_unidades": 39124.0,
    "atendidas_unidades": 29310.0,
    "perdidas_unidades": 9814.0,
    "fill_rate": 0.7491565279623761,
    "dias_sku_con_faltante": 3978,
    "tasa_dias_sku_con_faltante": 0.024812874251497006,
    "tasa_faltante_sobre_dias_con_demanda": 0.22396126562324062,
    "stock_medio_unidades_por_dia": 13105.327868852459,
    "stock_inicial_unidades": 12194.0,
    "stock_final_unidades": 12960.0,
    "pedidos_lineas": 8859,
    "pedidos_unidades": 33778.0,
    "recibidas_unidades": 30076.0,
    "transito_final_unidades": 3702.0,
    "holding_supuesto": 4712.655430136987,
    "compras_desembolsadas_supuesto": 384730.463,
    "costo_consumido_supuesto": 339613.9825,
    "valor_stock_inicial_supuesto": 134316.559,
    "valor_stock_final_supuesto": 134620.39500000002,
    "valor_transito_final_supuesto": 44812.644499999995
   },
   "historia_corta": {
    "skus": 675,
    "dias_sku_evaluables": 40500,
    "demanda_proxy_elegible_unidades": 3555.0,
    "atendidas_unidades": 2315.0,
    "perdidas_unidades": 1240.0,
    "fill_rate": 0.6511954992967651,
    "dias_sku_con_faltante": 536,
    "tasa_dias_sku_con_faltante": 0.013234567901234567,
    "tasa_faltante_sobre_dias_con_demanda": 0.28601921024546423,
    "stock_medio_unidades_por_dia": 2178.1147540983607,
    "stock_inicial_unidades": 1798.0,
    "stock_final_unidades": 2222.0,
    "pedidos_lineas": 1327,
    "pedidos_unidades": 3035.0,
    "recibidas_unidades": 2739.0,
    "transito_final_unidades": 296.0,
    "holding_supuesto": 1319.9701405479454,
    "compras_desembolsadas_supuesto": 46221.1035,
    "costo_consumido_supuesto": 34108.639500000005,
    "valor_stock_inicial_supuesto": 32248.918,
    "valor_stock_final_supuesto": 39918.047,
    "valor_transito_final_supuesto": 4443.334999999999
   },
   "identidad_valor": 7.275957614183426e-11,
   "conservacion": {
    "saldo_por_sku_ok": true,
    "demanda_ok": true,
    "pedidos_ok": true,
    "sistema": 0
   },
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "unit": "unidad base",
   "currency": "PEN"
  },
  {
   "scenario_id": "T07_L7_S7_R7_2026-06-01_2026-07-31",
   "L": 7,
   "S": 7,
   "R": 7,
   "policy": "promedio_28",
   "total": {
    "skus": 3347,
    "dias_sku_evaluables": 200820,
    "demanda_proxy_elegible_unidades": 42679.0,
    "atendidas_unidades": 34008.0,
    "perdidas_unidades": 8671.0,
    "fill_rate": 0.7968321657021017,
    "dias_sku_con_faltante": 3310,
    "tasa_dias_sku_con_faltante": 0.016482422069514988,
    "tasa_faltante_sobre_dias_con_demanda": 0.16856793644326748,
    "stock_medio_unidades_por_dia": 16648.39344262295,
    "stock_inicial_unidades": 13992.0,
    "stock_final_unidades": 17653.0,
    "pedidos_lineas": 8807,
    "pedidos_unidades": 43012.0,
    "recibidas_unidades": 37669.0,
    "transito_final_unidades": 5343.0,
    "holding_supuesto": 6785.72425041096,
    "compras_desembolsadas_supuesto": 515947.5295,
    "costo_consumido_supuesto": 403059.8065,
    "valor_stock_inicial_supuesto": 166565.477,
    "valor_stock_final_supuesto": 215187.986,
    "valor_transito_final_supuesto": 64265.214
   },
   "primaria": {
    "skus": 2672,
    "dias_sku_evaluables": 160320,
    "demanda_proxy_elegible_unidades": 39124.0,
    "atendidas_unidades": 31367.0,
    "perdidas_unidades": 7757.0,
    "fill_rate": 0.8017329516409365,
    "dias_sku_con_faltante": 2930,
    "tasa_dias_sku_con_faltante": 0.018275948103792416,
    "tasa_faltante_sobre_dias_con_demanda": 0.16495890102465938,
    "stock_medio_unidades_por_dia": 14431.360655737704,
    "stock_inicial_unidades": 12194.0,
    "stock_final_unidades": 15293.0,
    "pedidos_lineas": 7671,
    "pedidos_unidades": 39298.0,
    "recibidas_unidades": 34466.0,
    "transito_final_unidades": 4832.0,
    "holding_supuesto": 5356.88241150685,
    "compras_desembolsadas_supuesto": 457353.0455,
    "costo_consumido_supuesto": 364504.465,
    "valor_stock_inicial_supuesto": 134316.559,
    "valor_stock_final_supuesto": 168617.51400000002,
    "valor_transito_final_supuesto": 58547.6255
   },
   "historia_corta": {
    "skus": 675,
    "dias_sku_evaluables": 40500,
    "demanda_proxy_elegible_unidades": 3555.0,
    "atendidas_unidades": 2641.0,
    "perdidas_unidades": 914.0,
    "fill_rate": 0.7428973277074543,
    "dias_sku_con_faltante": 380,
    "tasa_dias_sku_con_faltante": 0.009382716049382716,
    "tasa_faltante_sobre_dias_con_demanda": 0.20277481323372465,
    "stock_medio_unidades_por_dia": 2217.032786885246,
    "stock_inicial_unidades": 1798.0,
    "stock_final_unidades": 2360.0,
    "pedidos_lineas": 1136,
    "pedidos_unidades": 3714.0,
    "recibidas_unidades": 3203.0,
    "transito_final_unidades": 511.0,
    "holding_supuesto": 1428.8418389041096,
    "compras_desembolsadas_supuesto": 58594.484,
    "costo_consumido_supuesto": 38555.3415,
    "valor_stock_inicial_supuesto": 32248.918,
    "valor_stock_final_supuesto": 46570.471999999994,
    "valor_transito_final_supuesto": 5717.5885
   },
   "identidad_valor": 7.275957614183426e-12,
   "conservacion": {
    "saldo_por_sku_ok": true,
    "demanda_ok": true,
    "pedidos_ok": true,
    "sistema": 0
   },
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "unit": "unidad base",
   "currency": "PEN"
  },
  {
   "scenario_id": "T07_L7_S7_R7_2026-06-01_2026-07-31",
   "L": 7,
   "S": 7,
   "R": 7,
   "policy": "rf_categoria_distribuido",
   "total": {
    "skus": 3347,
    "dias_sku_evaluables": 200820,
    "demanda_proxy_elegible_unidades": 42679.0,
    "atendidas_unidades": 34509.0,
    "perdidas_unidades": 8170.0,
    "fill_rate": 0.8085709599568874,
    "dias_sku_con_faltante": 3077,
    "tasa_dias_sku_con_faltante": 0.015322179065830097,
    "tasa_faltante_sobre_dias_con_demanda": 0.15670197596251784,
    "stock_medio_unidades_por_dia": 17890.786885245903,
    "stock_inicial_unidades": 13992.0,
    "stock_final_unidades": 18785.0,
    "pedidos_lineas": 8705,
    "pedidos_unidades": 44746.0,
    "recibidas_unidades": 39302.0,
    "transito_final_unidades": 5444.0,
    "holding_supuesto": 7184.865814794522,
    "compras_desembolsadas_supuesto": 536575.2535,
    "costo_consumido_supuesto": 409251.336,
    "valor_stock_inicial_supuesto": 166565.477,
    "valor_stock_final_supuesto": 227610.071,
    "valor_transito_final_supuesto": 66279.3235
   },
   "primaria": {
    "skus": 2672,
    "dias_sku_evaluables": 160320,
    "demanda_proxy_elegible_unidades": 39124.0,
    "atendidas_unidades": 31874.0,
    "perdidas_unidades": 7250.0,
    "fill_rate": 0.8146917493098865,
    "dias_sku_con_faltante": 2699,
    "tasa_dias_sku_con_faltante": 0.016835079840319362,
    "tasa_faltante_sobre_dias_con_demanda": 0.1519536088278347,
    "stock_medio_unidades_por_dia": 15682.393442622952,
    "stock_inicial_unidades": 12194.0,
    "stock_final_unidades": 16397.0,
    "pedidos_lineas": 7596,
    "pedidos_unidades": 40977.0,
    "recibidas_unidades": 36077.0,
    "transito_final_unidades": 4900.0,
    "holding_supuesto": 5793.677247123288,
    "compras_desembolsadas_supuesto": 478602.228,
    "costo_consumido_supuesto": 370793.4425,
    "valor_stock_inicial_supuesto": 134316.559,
    "valor_stock_final_supuesto": 181800.229,
    "valor_transito_final_supuesto": 60325.1155
   },
   "historia_corta": {
    "skus": 675,
    "dias_sku_evaluables": 40500,
    "demanda_proxy_elegible_unidades": 3555.0,
    "atendidas_unidades": 2635.0,
    "perdidas_unidades": 920.0,
    "fill_rate": 0.7412095639943741,
    "dias_sku_con_faltante": 378,
    "tasa_dias_sku_con_faltante": 0.009333333333333334,
    "tasa_faltante_sobre_dias_con_demanda": 0.2017075773745998,
    "stock_medio_unidades_por_dia": 2208.3934426229507,
    "stock_inicial_unidades": 1798.0,
    "stock_final_unidades": 2388.0,
    "pedidos_lineas": 1109,
    "pedidos_unidades": 3769.0,
    "recibidas_unidades": 3225.0,
    "transito_final_unidades": 544.0,
    "holding_supuesto": 1391.1885676712332,
    "compras_desembolsadas_supuesto": 57973.025499999996,
    "costo_consumido_supuesto": 38457.8935,
    "valor_stock_inicial_supuesto": 32248.918,
    "valor_stock_final_supuesto": 45809.842000000004,
    "valor_transito_final_supuesto": 5954.208
   },
   "identidad_valor": 5.820766091346741e-11,
   "conservacion": {
    "saldo_por_sku_ok": true,
    "demanda_ok": true,
    "pedidos_ok": true,
    "sistema": 0
   },
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "unit": "unidad base",
   "currency": "PEN"
  }
 ],
 "simulation_differences": [
  {
   "scenario": "L3_S0",
   "policy": "referencia_fija",
   "vs": "promedio_28",
   "cohorte": "total",
   "metrics": {
    "fill_rate": {
     "abs": -0.03992595890250472,
     "rel": -0.056390230988152726
    },
    "perdidas_unidades": {
     "abs": 1704.0,
     "rel": 0.13674664954658536
    },
    "tasa_dias_sku_con_faltante": {
     "abs": 0.004700727019221192,
     "rel": 0.197696335078534
    },
    "stock_medio_unidades_por_dia": {
     "abs": -428.42622950819714,
     "rel": -0.050283994704922626
    },
    "stock_final_unidades": {
     "abs": -1059.0,
     "rel": -0.1036913737393518
    },
    "pedidos_unidades": {
     "abs": -2763.0,
     "rel": -0.0930522345333917
    },
    "compras_desembolsadas_supuesto": {
     "abs": -40275.975999999966,
     "rel": -0.11131504494357973
    },
    "costo_consumido_supuesto": {
     "abs": -19608.563000000024,
     "rel": -0.05419466072551639
    },
    "holding_supuesto": {
     "abs": -324.46015452054735,
     "rel": -0.08901507068349472
    },
    "valor_stock_final_supuesto": {
     "abs": -20667.413000000015,
     "rel": -0.15793828380164512
    },
    "transito_final_unidades": {
     "abs": 0.0,
     "rel": null
    }
   }
  },
  {
   "scenario": "L3_S0",
   "policy": "referencia_fija",
   "vs": "promedio_28",
   "cohorte": "primaria",
   "metrics": {
    "fill_rate": {
     "abs": -0.035809221960944715,
     "rel": -0.05029978817362586
    },
    "perdidas_unidades": {
     "abs": 1401.0,
     "rel": 0.12430130423210008
    },
    "tasa_dias_sku_con_faltante": {
     "abs": 0.005039920159680637,
     "rel": 0.18878504672897187
    },
    "stock_medio_unidades_por_dia": {
     "abs": -377.8032786885242,
     "rel": -0.05199358371291848
    },
    "stock_final_unidades": {
     "abs": -902.0,
     "rel": -0.10297979221372303
    },
    "pedidos_unidades": {
     "abs": -2303.0,
     "rel": -0.08444868174984416
    },
    "compras_desembolsadas_supuesto": {
     "abs": -31862.128999999957,
     "rel": -0.09865418885826036
    },
    "costo_consumido_supuesto": {
     "abs": -15430.805000000051,
     "rel": -0.0474306820492401
    },
    "holding_supuesto": {
     "abs": -232.83171671232913,
     "rel": -0.08308934918111482
    },
    "valor_stock_final_supuesto": {
     "abs": -16431.324000000022,
     "rel": -0.15953599369705943
    },
    "transito_final_unidades": {
     "abs": 0.0,
     "rel": null
    }
   }
  },
  {
   "scenario": "L3_S0",
   "policy": "referencia_fija",
   "vs": "promedio_28",
   "cohorte": "historia_corta",
   "metrics": {
    "fill_rate": {
     "abs": -0.08523206751054857,
     "rel": -0.12811839323467236
    },
    "perdidas_unidades": {
     "abs": 303.0,
     "rel": 0.2546218487394958
    },
    "tasa_dias_sku_con_faltante": {
     "abs": 0.003358024691358024,
     "rel": 0.2747474747474747
    },
    "stock_medio_unidades_por_dia": {
     "abs": -50.62295081967204,
     "rel": -0.040376041108249036
    },
    "stock_final_unidades": {
     "abs": -157.0,
     "rel": -0.10797799174690509
    },
    "pedidos_unidades": {
     "abs": -460.0,
     "rel": -0.18992568125516102
    },
    "compras_desembolsadas_supuesto": {
     "abs": -8413.847000000002,
     "rel": -0.2165622060188272
    },
    "costo_consumido_supuesto": {
     "abs": -4177.758000000005,
     "rel": -0.11451111604028993
    },
    "holding_supuesto": {
     "abs": -91.62843780821913,
     "rel": -0.10871680278139798
    },
    "valor_stock_final_supuesto": {
     "abs": -4236.089,
     "rel": -0.15203242644271425
    },
    "transito_final_unidades": {
     "abs": 0.0,
     "rel": null
    }
   }
  },
  {
   "scenario": "L3_S0",
   "policy": "rf_categoria_distribuido",
   "vs": "promedio_28",
   "cohorte": "total",
   "metrics": {
    "fill_rate": {
     "abs": 0.01672953911759889,
     "rel": 0.023628301012641573
    },
    "perdidas_unidades": {
     "abs": -714.0,
     "rel": -0.0572987721691678
    },
    "tasa_dias_sku_con_faltante": {
     "abs": -0.0014042426053181949,
     "rel": -0.05905759162303663
    },
    "stock_medio_unidades_por_dia": {
     "abs": 940.2950819672133,
     "rel": 0.11036157374626729
    },
    "stock_final_unidades": {
     "abs": 776.0,
     "rel": 0.07598159208851464
    },
    "pedidos_unidades": {
     "abs": 1490.0,
     "rel": 0.05018017714612872
    },
    "compras_desembolsadas_supuesto": {
     "abs": 17425.16749999998,
     "rel": 0.04815980880045972
    },
    "costo_consumido_supuesto": {
     "abs": 8599.3505,
     "rel": 0.023767110461245893
    },
    "holding_supuesto": {
     "abs": 305.93003287671263,
     "rel": 0.08393136451828902
    },
    "valor_stock_final_supuesto": {
     "abs": 8825.81699999998,
     "rel": 0.06744600256100655
    },
    "transito_final_unidades": {
     "abs": 0.0,
     "rel": null
    }
   }
  },
  {
   "scenario": "L3_S0",
   "policy": "rf_categoria_distribuido",
   "vs": "promedio_28",
   "cohorte": "primaria",
   "metrics": {
    "fill_rate": {
     "abs": 0.0170994785809222,
     "rel": 0.024018956665350238
    },
    "perdidas_unidades": {
     "abs": -669.0,
     "rel": -0.05935586904445036
    },
    "tasa_dias_sku_con_faltante": {
     "abs": -0.0016342315369261493,
     "rel": -0.06121495327102809
    },
    "stock_medio_unidades_por_dia": {
     "abs": 881.8196721311479,
     "rel": 0.12135671533027866
    },
    "stock_final_unidades": {
     "abs": 705.0,
     "rel": 0.08048864025573696
    },
    "pedidos_unidades": {
     "abs": 1374.0,
     "rel": 0.05038319093542591
    },
    "compras_desembolsadas_supuesto": {
     "abs": 16715.179000000062,
     "rel": 0.05175493532982795
    },
    "costo_consumido_supuesto": {
     "abs": 8159.001500000013,
     "rel": 0.025078860499226863
    },
    "holding_supuesto": {
     "abs": 291.411016712329,
     "rel": 0.10399421549921611
    },
    "valor_stock_final_supuesto": {
     "abs": 8556.17749999999,
     "rel": 0.08307415030650715
    },
    "transito_final_unidades": {
     "abs": 0.0,
     "rel": null
    }
   }
  },
  {
   "scenario": "L3_S0",
   "policy": "rf_categoria_distribuido",
   "vs": "promedio_28",
   "cohorte": "historia_corta",
   "metrics": {
    "fill_rate": {
     "abs": 0.012658227848101222,
     "rel": 0.019027484143763148
    },
    "perdidas_unidades": {
     "abs": -45.0,
     "rel": -0.037815126050420166
    },
    "tasa_dias_sku_con_faltante": {
     "abs": -0.0004938271604938271,
     "rel": -0.040404040404040394
    },
    "stock_medio_unidades_por_dia": {
     "abs": 58.47540983606564,
     "rel": 0.04663903453145231
    },
    "stock_final_unidades": {
     "abs": 71.0,
     "rel": 0.04883081155433287
    },
    "pedidos_unidades": {
     "abs": 116.0,
     "rel": 0.04789430222956235
    },
    "compras_desembolsadas_supuesto": {
     "abs": 709.9884999999995,
     "rel": 0.018274241949966283
    },
    "costo_consumido_supuesto": {
     "abs": 440.3489999999947,
     "rel": 0.012069836366114303
    },
    "holding_supuesto": {
     "abs": 14.519016164383629,
     "rel": 0.017226759013691657
    },
    "valor_stock_final_supuesto": {
     "abs": 269.6394999999975,
     "rel": 0.009677310238240951
    },
    "transito_final_unidades": {
     "abs": 0.0,
     "rel": null
    }
   }
  },
  {
   "scenario": "L7_S7",
   "policy": "referencia_fija",
   "vs": "promedio_28",
   "cohorte": "total",
   "metrics": {
    "fill_rate": {
     "abs": -0.05583542257316243,
     "rel": -0.07007174782404138
    },
    "perdidas_unidades": {
     "abs": 2383.0,
     "rel": 0.2748241263983393
    },
    "tasa_dias_sku_con_faltante": {
     "abs": 0.005995418782989741,
     "rel": 0.3637462235649547
    },
    "stock_medio_unidades_por_dia": {
     "abs": -1364.9508196721308,
     "rel": -0.08198693912276278
    },
    "stock_final_unidades": {
     "abs": -2471.0,
     "rel": -0.13997620800997
    },
    "pedidos_unidades": {
     "abs": -6199.0,
     "rel": -0.1441225704454571
    },
    "compras_desembolsadas_supuesto": {
     "abs": -84995.96299999999,
     "rel": -0.16473761020305455
    },
    "costo_consumido_supuesto": {
     "abs": -29337.184500000032,
     "rel": -0.07278618216674014
    },
    "holding_supuesto": {
     "abs": -753.0986797260266,
     "rel": -0.11098280035184412
    },
    "valor_stock_final_supuesto": {
     "abs": -40649.54400000002,
     "rel": -0.1889024789701783
    },
    "transito_final_unidades": {
     "abs": -1345.0,
     "rel": -0.25173123713269696
    }
   }
  },
  {
   "scenario": "L7_S7",
   "policy": "referencia_fija",
   "vs": "promedio_28",
   "cohorte": "primaria",
   "metrics": {
    "fill_rate": {
     "abs": -0.05257642367856041,
     "rel": -0.06557847419262275
    },
    "perdidas_unidades": {
     "abs": 2057.0,
     "rel": 0.26517983756606933
    },
    "tasa_dias_sku_con_faltante": {
     "abs": 0.00653692614770459,
     "rel": 0.35767918088737194
    },
    "stock_medio_unidades_por_dia": {
     "abs": -1326.0327868852455,
     "rel": -0.0918854998165425
    },
    "stock_final_unidades": {
     "abs": -2333.0,
     "rel": -0.15255345582946447
    },
    "pedidos_unidades": {
     "abs": -5520.0,
     "rel": -0.14046516362155834
    },
    "compras_desembolsadas_supuesto": {
     "abs": -72622.58250000002,
     "rel": -0.15878889014635417
    },
    "costo_consumido_supuesto": {
     "abs": -24890.482500000042,
     "rel": -0.06828580961278496
    },
    "holding_supuesto": {
     "abs": -644.2269813698631,
     "rel": -0.12026154988693265
    },
    "valor_stock_final_supuesto": {
     "abs": -33997.119000000006,
     "rel": -0.2016227033213169
    },
    "transito_final_unidades": {
     "abs": -1130.0,
     "rel": -0.23385761589403972
    }
   }
  },
  {
   "scenario": "L7_S7",
   "policy": "referencia_fija",
   "vs": "promedio_28",
   "cohorte": "historia_corta",
   "metrics": {
    "fill_rate": {
     "abs": -0.09170182841068919,
     "rel": -0.12343809163195761
    },
    "perdidas_unidades": {
     "abs": 326.0,
     "rel": 0.35667396061269147
    },
    "tasa_dias_sku_con_faltante": {
     "abs": 0.003851851851851851,
     "rel": 0.41052631578947363
    },
    "stock_medio_unidades_por_dia": {
     "abs": -38.918032786885306,
     "rel": -0.017554107912658358
    },
    "stock_final_unidades": {
     "abs": -138.0,
     "rel": -0.05847457627118644
    },
    "pedidos_unidades": {
     "abs": -679.0,
     "rel": -0.18282175551965535
    },
    "compras_desembolsadas_supuesto": {
     "abs": -12373.3805,
     "rel": -0.2111697152243887
    },
    "costo_consumido_supuesto": {
     "abs": -4446.7019999999975,
     "rel": -0.11533296884427796
    },
    "holding_supuesto": {
     "abs": -108.87169835616419,
     "rel": -0.07619576596361875
    },
    "valor_stock_final_supuesto": {
     "abs": -6652.424999999996,
     "rel": -0.1428464156429421
    },
    "transito_final_unidades": {
     "abs": -215.0,
     "rel": -0.4207436399217221
    }
   }
  },
  {
   "scenario": "L7_S7",
   "policy": "rf_categoria_distribuido",
   "vs": "promedio_28",
   "cohorte": "total",
   "metrics": {
    "fill_rate": {
     "abs": 0.011738794254785745,
     "rel": 0.014731827805222326
    },
    "perdidas_unidades": {
     "abs": -501.0,
     "rel": -0.057778802906239185
    },
    "tasa_dias_sku_con_faltante": {
     "abs": -0.001160243003684891,
     "rel": -0.07039274924471293
    },
    "stock_medio_unidades_por_dia": {
     "abs": 1242.3934426229534,
     "rel": 0.07462542538442164
    },
    "stock_final_unidades": {
     "abs": 1132.0,
     "rel": 0.06412507789044355
    },
    "pedidos_unidades": {
     "abs": 1734.0,
     "rel": 0.04031433088440435
    },
    "compras_desembolsadas_supuesto": {
     "abs": 20627.723999999987,
     "rel": 0.03998027477714667
    },
    "costo_consumido_supuesto": {
     "abs": 6191.529500000004,
     "rel": 0.015361317105182513
    },
    "holding_supuesto": {
     "abs": 399.1415643835617,
     "rel": 0.058820775742455006
    },
    "valor_stock_final_supuesto": {
     "abs": 12422.084999999992,
     "rel": 0.057726666023074316
    },
    "transito_final_unidades": {
     "abs": 101.0,
     "rel": 0.01890323788134007
    }
   }
  },
  {
   "scenario": "L7_S7",
   "policy": "rf_categoria_distribuido",
   "vs": "promedio_28",
   "cohorte": "primaria",
   "metrics": {
    "fill_rate": {
     "abs": 0.012958797668950028,
     "rel": 0.01616348391621771
    },
    "perdidas_unidades": {
     "abs": -507.0,
     "rel": -0.06536031971122856
    },
    "tasa_dias_sku_con_faltante": {
     "abs": -0.0014408682634730538,
     "rel": -0.078839590443686
    },
    "stock_medio_unidades_por_dia": {
     "abs": 1251.0327868852473,
     "rel": 0.08668848466397758
    },
    "stock_final_unidades": {
     "abs": 1104.0,
     "rel": 0.07218989079971229
    },
    "pedidos_unidades": {
     "abs": 1679.0,
     "rel": 0.04272482060155733
    },
    "compras_desembolsadas_supuesto": {
     "abs": 21249.182499999995,
     "rel": 0.04646122445029175
    },
    "costo_consumido_supuesto": {
     "abs": 6288.977499999979,
     "rel": 0.017253499212965685
    },
    "holding_supuesto": {
     "abs": 436.7948356164379,
     "rel": 0.08153900012406112
    },
    "valor_stock_final_supuesto": {
     "abs": 13182.714999999967,
     "rel": 0.0781811728050976
    },
    "transito_final_unidades": {
     "abs": 68.0,
     "rel": 0.014072847682119206
    }
   }
  },
  {
   "scenario": "L7_S7",
   "policy": "rf_categoria_distribuido",
   "vs": "promedio_28",
   "cohorte": "historia_corta",
   "metrics": {
    "fill_rate": {
     "abs": -0.0016877637130802148,
     "rel": -0.0022718667171526554
    },
    "perdidas_unidades": {
     "abs": 6.0,
     "rel": 0.006564551422319475
    },
    "tasa_dias_sku_con_faltante": {
     "abs": -4.938271604938184e-05,
     "rel": -0.005263157894736748
    },
    "stock_medio_unidades_por_dia": {
     "abs": -8.639344262295253,
     "rel": -0.003896804915741838
    },
    "stock_final_unidades": {
     "abs": 28.0,
     "rel": 0.011864406779661017
    },
    "pedidos_unidades": {
     "abs": 55.0,
     "rel": 0.014808831448572967
    },
    "compras_desembolsadas_supuesto": {
     "abs": -621.4585000000006,
     "rel": -0.0106060922048567
    },
    "costo_consumido_supuesto": {
     "abs": -97.44800000000396,
     "rel": -0.0025274837729035277
    },
    "holding_supuesto": {
     "abs": -37.65327123287648,
     "rel": -0.026352301708743153
    },
    "valor_stock_final_supuesto": {
     "abs": -760.6299999999901,
     "rel": -0.01633288148765145
    },
    "transito_final_unidades": {
     "abs": 33.0,
     "rel": 0.06457925636007827
    }
   }
  }
 ],
 "assumptions": {
  "L": [
   3,
   7,
   14
  ],
  "S": [
   0,
   7,
   14
  ],
  "R": 7,
  "factor_costo_sobre_mediana_precio": 0.65,
  "holding_anual": 0.2,
  "dias_anio": 365,
  "holding_diario": 0.0005479452054794521,
  "escenario_principal": {
   "L": 7,
   "S": 7
  },
  "moneda": "PEN",
  "unidad": "unidad base",
  "demanda": "proxy: venta positiva observada, posiblemente censurada por stock real desconocido",
  "limites": [
   "cuatro folds solapados de desarrollo",
   "costo y holding supuestos",
   "sin MOQ, proveedores ni plazos reales",
   "un almacén",
   "universo fijo sin SKU nuevos",
   "no autoriza compras"
  ]
 }
};

export const realBacktestList: Page<BacktestItem> = {
 "items": [
  {
   "backtest_id": "bt-hist-20260710-52b01cd999dd",
   "kind": "T07_desarrollo",
   "label": "Backtest de desarrollo T07 (4 folds solapados y simulación 01/06 a 31/07)",
   "folds": [
    "G1",
    "G2",
    "G3",
    "G4"
   ],
   "created": "2026-10-17T17:17:27Z",
   "run_id": "hist-20260710-52b01cd999dd",
   "scenario_id": "T07_simulacion_2026-06-01_2026-07-31",
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "disclaimer": "Inventario simulado con supuestos; no corresponde al inventario real de la empresa. Resultados de desarrollo sobre meses ya conocidos; no demuestran impacto en la empresa ni autorizan compras.",
   "run": {
    "run_id": "hist-20260710-52b01cd999dd",
    "run_label": "Corrida histórica de desarrollo al 10/07/2026",
    "cutoff": "2026-07-10",
    "generated_at": "2026-10-17T16:45:00Z",
    "published_at": "2026-10-17T17:17:30Z",
    "age_days_at_view": 99,
    "is_active": true
   }
  }
 ],
 "page": 1,
 "page_size": 50,
 "total": 1,
 "has_more": false
};

export const realRunSummary: RunSummary = {
 "run_id": "hist-20260710-52b01cd999dd",
 "run_label": "Corrida histórica de desarrollo al 10/07/2026",
 "cutoff": "2026-07-10",
 "generated_at": "2026-10-17T16:45:00Z",
 "published_at": "2026-10-17T17:17:30Z",
 "age_days_at_view": 99,
 "is_active": true,
 "kind": "historical_development",
 "status": "completed",
 "origin": "2026-07-10",
 "target_start": "2026-07-11",
 "target_end": "2026-07-31",
 "horizon_days": 21,
 "evaluation_period": {
  "start": "2026-07-11",
  "end": "2026-07-31",
  "days": 21,
  "evaluable_days": 21,
  "excluded_days": [],
  "note": "backtest histórico: 'observed' es la venta real ya ocurrida; agosto no se usó"
 },
 "method": {
  "chosen": "promedio_28",
  "comparator": "rf_categoria_distribuido",
  "control": "cero",
  "note": "La regla provisional de T07 no se cumplió para el RF distribuido; se mantiene promedio_28. Control 'cero' = pronóstico 0 (derivado)."
 },
 "counts": {
  "forecasts_sku": 76587,
  "forecasts_categoria": 756,
  "recommendations": 3647,
  "recommendations_ok": 3347,
  "recommendations_sin_snapshot": 300,
  "recommendations_con_pedido": 640,
  "backtests": 1
 },
 "coverage": {
  "skus_pronosticados": 3647,
  "skus_con_recomendacion": 3347,
  "skus_sin_snapshot": 300,
  "categorias": 36,
  "skus_categoria_desconocida": 0
 },
 "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
 "disclaimer": "Inventario simulado con supuestos; no corresponde al inventario real de la empresa"
};

export const realRunDetail: RunDetail = {
 "run_id": "hist-20260710-52b01cd999dd",
 "run_label": "Corrida histórica de desarrollo al 10/07/2026",
 "cutoff": "2026-07-10",
 "generated_at": "2026-10-17T16:45:00Z",
 "published_at": "2026-10-17T17:17:30Z",
 "age_days_at_view": 99,
 "is_active": true,
 "kind": "historical_development",
 "status": "completed",
 "method": {
  "chosen": "promedio_28",
  "comparator": "rf_categoria_distribuido",
  "control": "cero",
  "note": "La regla provisional de T07 no se cumplió para el RF distribuido; se mantiene promedio_28. Control 'cero' = pronóstico 0 (derivado)."
 },
 "counts": {
  "forecasts_sku": 76587,
  "forecasts_categoria": 756,
  "recommendations": 3647,
  "recommendations_ok": 3347,
  "recommendations_sin_snapshot": 300,
  "recommendations_con_pedido": 640,
  "backtests": 1
 },
 "coverage": {
  "skus_pronosticados": 3647,
  "skus_con_recomendacion": 3347,
  "skus_sin_snapshot": 300,
  "categorias": 36,
  "skus_categoria_desconocida": 0
 },
 "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
 "disclaimer": "Inventario simulado con supuestos; no corresponde al inventario real de la empresa",
 "artifacts": [
  {
   "name": "predicciones_folds.csv.gz",
   "sha256": "4f7b2110b26017a23b76d8a59184a22edfeebbc47031170533593c1754bc2512",
   "size_bytes": 2250114
  },
  {
   "name": "simulacion_series.npz",
   "sha256": "8497a1354f448083dba608e763c77724ed78c17d61e4c215b687253672136409",
   "size_bytes": 5154201
  },
  {
   "name": "T07_METRICAS.json",
   "sha256": "6d79a51cfc9a77120730e66f81f0d59d81f5ff6e0ea24ebc2a35b3065a86472f",
   "size_bytes": 362183
  }
 ]
};

export const realRecoDetail: Recommendation = {
 "run_id": "hist-20260710-52b01cd999dd",
 "scenario_id": "T07_L7_S7_promedio_28_2026-07-10",
 "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
 "snapshot_date": "2026-07-10",
 "sku": "1010004",
 "almacen": "1",
 "categoria": "HIGIENE CAPILAR",
 "horizon_days": 14,
 "lead_time_days": 7,
 "review_days": 7,
 "safety_days": 7,
 "currency": "PEN",
 "unit": "unidad base",
 "origin": "2026-07-10",
 "forecast_from": "2026-07-11",
 "forecast_to": "2026-07-24",
 "model": "promedio_28",
 "status": "ok",
 "reason": null,
 "on_hand": 5,
 "in_transit": 2,
 "mean_28": 0.3571428571,
 "forecast_14d": 4.999999999400001,
 "unit_cost_assumed": 42.25,
 "safety": 2.4999999997,
 "target": 8,
 "position": 7,
 "order_qty": 1,
 "order_value_assumed": 42.25,
 "transit_breakdown": {
  "ordered_until_snapshot": 19,
  "received_until_snapshot": 17
 },
 "explanation_steps": [
  "1. Origen: cierre del 10/07/2026 de la trayectoria simulada T07_L7_S7_promedio_28_2026-07-10 (plazo 7 días, revisión cada 7, seguridad 7 días).",
  "2. Saldo simulado en mano al cierre del 10/07: 5 unidades base.",
  "3. En tránsito al 10/07 = pedidos emitidos hasta esa fecha (19) menos recepciones hasta esa fecha (17) = 2 unidades base.",
  "4. Posición = 5 + 2 = 7 unidades base.",
  "5. Promedio diario de 28 días conocido al 10/07 = 0.357143 unidades base/día.",
  "6. Pronóstico de 14 días (11/07 a 24/07) = 5.000000 unidades base.",
  "7. Seguridad = 7 × 0.357143 = 2.500000 unidades base.",
  "8. Objetivo = techo(redondeo a 9 decimales de 7.499999999) = 8 unidades base.",
  "9. Pedido sugerido = máx(0, 8 - 7) = 1 unidades base.",
  "10. Costo unitario supuesto (65 % de la mediana de precio base hasta el 31/05) = PEN 42.2500; valor supuesto del pedido = PEN 42.25.",
  "Sugerencia hipotética de vista previa; no es un pedido ejecutado. Inventario simulado con supuestos; no corresponde al inventario real de la empresa. La demanda es la venta observada: los faltantes por stock real son desconocidos."
 ],
 "explanation": "1. Origen: cierre del 10/07/2026 de la trayectoria simulada T07_L7_S7_promedio_28_2026-07-10 (plazo 7 días, revisión cada 7, seguridad 7 días).\n2. Saldo simulado en mano al cierre del 10/07: 5 unidades base.\n3. En tránsito al 10/07 = pedidos emitidos hasta esa fecha (19) menos recepciones hasta esa fecha (17) = 2 unidades base.\n4. Posición = 5 + 2 = 7 unidades base.\n5. Promedio diario de 28 días conocido al 10/07 = 0.357143 unidades base/día.\n6. Pronóstico de 14 días (11/07 a 24/07) = 5.000000 unidades base.\n7. Seguridad = 7 × 0.357143 = 2.500000 unidades base.\n8. Objetivo = techo(redondeo a 9 decimales de 7.499999999) = 8 unidades base.\n9. Pedido sugerido = máx(0, 8 - 7) = 1 unidades base.\n10. Costo unitario supuesto (65 % de la mediana de precio base hasta el 31/05) = PEN 42.2500; valor supuesto del pedido = PEN 42.25.\nSugerencia hipotética de vista previa; no es un pedido ejecutado. Inventario simulado con supuestos; no corresponde al inventario real de la empresa. La demanda es la venta observada: los faltantes por stock real son desconocidos.",
 "run": {
  "run_id": "hist-20260710-52b01cd999dd",
  "run_label": "Corrida histórica de desarrollo al 10/07/2026",
  "cutoff": "2026-07-10",
  "generated_at": "2026-10-17T16:45:00Z",
  "published_at": "2026-10-17T17:17:30Z",
  "age_days_at_view": 99,
  "is_active": true
 },
 "disclaimer": "Inventario simulado con supuestos; no corresponde al inventario real de la empresa"
};

export const realRecoPage: RecoPage = {
 "items": [
  {
   "run_id": "hist-20260710-52b01cd999dd",
   "scenario_id": "T07_L7_S7_promedio_28_2026-07-10",
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "snapshot_date": "2026-07-10",
   "sku": "26120367",
   "almacen": "1",
   "categoria": "PRODUCTOS DE TINTURACION",
   "horizon_days": 14,
   "lead_time_days": 7,
   "review_days": 7,
   "safety_days": 7,
   "currency": "PEN",
   "unit": "unidad base",
   "origin": "2026-07-10",
   "forecast_from": "2026-07-11",
   "forecast_to": "2026-07-24",
   "model": "promedio_28",
   "status": "ok",
   "reason": null,
   "on_hand": 0,
   "in_transit": 0,
   "mean_28": 3.285714286,
   "forecast_14d": 46.00000000400001,
   "unit_cost_assumed": 5.525,
   "safety": 23.000000002,
   "target": 70,
   "position": 0,
   "order_qty": 70,
   "order_value_assumed": 386.75,
   "transit_breakdown": {
    "ordered_until_snapshot": 75,
    "received_until_snapshot": 75
   },
   "explanation_steps": [
    "1. Origen: cierre del 10/07/2026 de la trayectoria simulada T07_L7_S7_promedio_28_2026-07-10 (plazo 7 días, revisión cada 7, seguridad 7 días).",
    "2. Saldo simulado en mano al cierre del 10/07: 0 unidades base.",
    "3. En tránsito al 10/07 = pedidos emitidos hasta esa fecha (75) menos recepciones hasta esa fecha (75) = 0 unidades base.",
    "4. Posición = 0 + 0 = 0 unidades base.",
    "5. Promedio diario de 28 días conocido al 10/07 = 3.285714 unidades base/día.",
    "6. Pronóstico de 14 días (11/07 a 24/07) = 46.000000 unidades base.",
    "7. Seguridad = 7 × 3.285714 = 23.000000 unidades base.",
    "8. Objetivo = techo(redondeo a 9 decimales de 69.000000006) = 70 unidades base.",
    "9. Pedido sugerido = máx(0, 70 - 0) = 70 unidades base.",
    "10. Costo unitario supuesto (65 % de la mediana de precio base hasta el 31/05) = PEN 5.5250; valor supuesto del pedido = PEN 386.75.",
    "Sugerencia hipotética de vista previa; no es un pedido ejecutado. Inventario simulado con supuestos; no corresponde al inventario real de la empresa. La demanda es la venta observada: los faltantes por stock real son desconocidos."
   ]
  },
  {
   "run_id": "hist-20260710-52b01cd999dd",
   "scenario_id": "T07_L7_S7_promedio_28_2026-07-10",
   "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
   "snapshot_date": "2026-07-10",
   "sku": "26090257",
   "almacen": "1",
   "categoria": "PRODUCTOS DE TINTURACION",
   "horizon_days": 14,
   "lead_time_days": 7,
   "review_days": 7,
   "safety_days": 7,
   "currency": "PEN",
   "unit": "unidad base",
   "origin": "2026-07-10",
   "forecast_from": "2026-07-11",
   "forecast_to": "2026-07-24",
   "model": "promedio_28",
   "status": "ok",
   "reason": null,
   "on_hand": 47,
   "in_transit": 18,
   "mean_28": 6.321428571,
   "forecast_14d": 88.49999999399999,
   "unit_cost_assumed": 16.25,
   "safety": 44.249999997,
   "target": 133,
   "position": 65,
   "order_qty": 68,
   "order_value_assumed": 1105.0,
   "transit_breakdown": {
    "ordered_until_snapshot": 189,
    "received_until_snapshot": 171
   },
   "explanation_steps": [
    "1. Origen: cierre del 10/07/2026 de la trayectoria simulada T07_L7_S7_promedio_28_2026-07-10 (plazo 7 días, revisión cada 7, seguridad 7 días).",
    "2. Saldo simulado en mano al cierre del 10/07: 47 unidades base.",
    "3. En tránsito al 10/07 = pedidos emitidos hasta esa fecha (189) menos recepciones hasta esa fecha (171) = 18 unidades base.",
    "4. Posición = 47 + 18 = 65 unidades base.",
    "5. Promedio diario de 28 días conocido al 10/07 = 6.321429 unidades base/día.",
    "6. Pronóstico de 14 días (11/07 a 24/07) = 88.500000 unidades base.",
    "7. Seguridad = 7 × 6.321429 = 44.250000 unidades base.",
    "8. Objetivo = techo(redondeo a 9 decimales de 132.749999991) = 133 unidades base.",
    "9. Pedido sugerido = máx(0, 133 - 65) = 68 unidades base.",
    "10. Costo unitario supuesto (65 % de la mediana de precio base hasta el 31/05) = PEN 16.2500; valor supuesto del pedido = PEN 1105.00.",
    "Sugerencia hipotética de vista previa; no es un pedido ejecutado. Inventario simulado con supuestos; no corresponde al inventario real de la empresa. La demanda es la venta observada: los faltantes por stock real son desconocidos."
   ]
  }
 ],
 "page": 1,
 "page_size": 3,
 "total": 3647,
 "has_more": true,
 "run": {
  "run_id": "hist-20260710-52b01cd999dd",
  "run_label": "Corrida histórica de desarrollo al 10/07/2026",
  "cutoff": "2026-07-10",
  "generated_at": "2026-10-17T16:45:00Z",
  "published_at": "2026-10-17T17:17:30Z",
  "age_days_at_view": 99,
  "is_active": true
 },
 "provenance": "SYNTHETIC_NOT_REAL_INVENTORY",
 "disclaimer": "Inventario simulado con supuestos; no corresponde al inventario real de la empresa",
 "nota": "Sugerencia hipotética de vista previa; no es un pedido ejecutado."
};

