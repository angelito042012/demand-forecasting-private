// Run a copy of this file beside workbook_payload.json with the bundled artifact-tool.
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
// Windows may deny junction creation; resolve the same bundled dependency explicitly.
const requireBundled = createRequire(process.env.ARTIFACT_RUNTIME_ROOT + '/package.json');
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(requireBundled.resolve('@oai/artifact-tool')).href);
const root = new URL('.', import.meta.url);
const p = JSON.parse(await fs.readFile(new URL('workbook_payload.json', root), 'utf8'));
const mode = process.argv[2];
const wb = Workbook.create();
const out = new URL('03_excel/', root);
await fs.mkdir(out, {recursive:true});
const numeric = new Set(['cantidad','importe','fila','ocurrencia','rango','meses_venta','meses_compra','dias_venta','unidades_vendidas','saldo_inicial_minimo_calculado','entradas_documentadas','salidas_documentadas','ajustes_incorporados','saldo_final_calculado','saldo_inicio_dia','saldo_fin_dia','unidades_en_segundas_copias','saldo_inicial_alternativo_sin_segundas_copias','saldo_final_alternativo_sin_segundas_copias']);
function letter(n){let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
function table(name, rows, keys, note) {
  const s=wb.worksheets.add(name); s.showGridLines=false;
  const end=letter(keys.length-1), last=rows.length+4;
  s.getRange('A1:F1').merge(); s.getRange('A1').values=[[name.replaceAll('_',' ')]];
  s.getRange('A1:F1').format={fill:'#153E52',font:{bold:true,color:'#FFFFFF',size:16},rowHeight:32};
  s.getRange('A2:F3').merge(); s.getRange('A2').values=[[note]];
  s.getRange('A2:F3').format={wrapText:true,font:{size:11,color:'#384C58'},fill:'#EAF2F5',rowHeight:25};
  s.getRange(`A4:${end}4`).values=[keys.map(k=>k.replaceAll('_',' '))];
  s.getRange(`A4:${end}4`).format={fill:'#287681',font:{bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:48};
  if(rows.length)s.getRange(`A5:${end}${last}`).values=rows.map(r=>keys.map(k=>{
    const v=r[k]; if(v===undefined||v===null)return null;
    if(numeric.has(k))return Number(v);
    if((k==='fecha'||k.startsWith('fecha_')||k==='corte_seleccion')&&/^\d{4}-\d{2}-\d{2}$/.test(v))return new Date(v+'T00:00:00Z');
    return typeof v==='object'?JSON.stringify(v):v;
  }));
  s.getRange(`A4:${end}${Math.max(5,last)}`).format.font.size=11;
  keys.forEach((k,i)=>{const c=letter(i),r=s.getRange(`${c}4:${c}${Math.max(5,last)}`);r.format.columnWidth=k==='producto'?47:['decision','explicacion','motivo'].includes(k)?70:k==='archivo'?28:21;
    if(['producto','decision','explicacion','motivo'].includes(k)){
      s.getRange(`${c}5:${c}${Math.max(5,last)}`).format.wrapText=true;
      s.getRange(`A5:${end}${Math.max(5,last)}`).format.rowHeight=k==='producto'?32:48;
    }
    if(numeric.has(k))s.getRange(`${c}5:${c}${Math.max(5,last)}`).setNumberFormat(k==='importe'||rows.some(r=>r[k]!=null&&!Number.isInteger(Number(r[k])))?'#,##0.00':'#,##0');
    if(k==='fecha'||k.startsWith('fecha_')||k==='corte_seleccion')s.getRange(`${c}5:${c}${Math.max(5,last)}`).setNumberFormat('dd/mm/yyyy');
  });
  s.freezePanes.freezeRows(4); return s;
}
const fields=['fecha','producto_id','producto','cantidad','unidad','moneda','importe','clasificacion','almacen','tipo_documento','documento_id','grupo_repeticion','ocurrencia','dia_excluido_pronostico','archivo','hoja','fila','sha256_origen','registro_id'];
let file, first;
if(mode==='ventas'){
 file='01_Ventas_grupo.xlsx';first='Ventas';
 table(first,p.sales,fields,'50 productos | Marzo–septiembre 2026. Ventas documentadas; cantidades en unidad base. Procedencia en las columnas finales.');
 table('Notas_de_credito',p.credits,fields,'Documentos financieros separados. No se supone que la mercadería volvió físicamente al almacén.');
}else if(mode==='compras'){
 file='02_Compras_grupo.xlsx';first='Compras';
 table(first,p.purchases,fields,'50 productos | Marzo–septiembre 2026. Se conservan compras sin cargo; no se inventan precios ni tipos de cambio.');
}else if(mode==='inventario'){
 file='03_Inventario_calculado.xlsx';first='Saldo_calculado';
 const keys=['producto_id','producto','saldo_inicial_minimo_calculado','entradas_documentadas','salidas_documentadas','saldo_final_calculado','conteo_fisico','fecha_inicial','fecha_final','origen_saldo'];
 const s=table(first,p.stock,keys,'Saldo retrospectivo bajo supuestos, NO conteo físico. Del 01/03 al 30/09/2026. No usar este saldo para entrenar ni evaluar pronósticos.');
 const dk=['fecha','producto_id','saldo_inicio_dia','entradas_documentadas','salidas_documentadas','ajustes_incorporados','saldo_fin_dia','origen_saldo','conteo_fisico_verificado'];
 const d=table('Balance_diario',p.daily,dk,'Compras como entradas en fecha del documento y ventas como salidas. Ajustes incorporados = 0 es un supuesto, no una comprobación.');
 const starts=[],ends=[];
 for(let i=0;i<p.daily.length;i++){const row=i+5, group=Math.floor(i/214)+5;starts.push([i%214===0?`='Saldo_calculado'!C${group}`:`=G${row-1}`]);ends.push([`=C${row}+D${row}-E${row}+F${row}`]);}
 d.getRange(`C5:C${p.daily.length+4}`).formulas=starts;d.getRange(`G5:G${p.daily.length+4}`).formulas=ends;
 for(let i=0;i<p.stock.length;i++){const row=i+5,a=i*214+5,b=a+213;
 s.getRange(`D${row}:F${row}`).formulas=[[`=SUM('Balance_diario'!D${a}:D${b})`,`=SUM('Balance_diario'!E${a}:E${b})`,`='Balance_diario'!G${b}`]];}
 table('Supuestos',p.parameters,['parametro','valor','unidad','naturaleza','explicacion'],'Parámetros de trabajo académico. Los datos no disponibles permanecen vacíos; no equivalen a cero.');
}else if(mode==='control'){
 file='04_Control_y_decisiones.xlsx';first='Decisiones';
 const decisions=[
 {asunto:'Ventas válidas',cantidad:101080,decision:'Conservar todo el universo para pronóstico; grupo de 50 solo para reposición.'},
 {asunto:'Compras válidas',cantidad:4779,decision:'Conservar unidades y moneda original; incluye 1224 líneas sin cargo.'},
 {asunto:'Notas de crédito',cantidad:664,decision:'Separar; no convertir automáticamente en devolución física.'},
 {asunto:'Filas en cuarentena',cantidad:2,decision:'Una venta con conversión incompatible y una compra con importe negativo.'},
 {asunto:'Copias exactas adicionales',cantidad:6,decision:'Conservar marcadas: no hay confirmación empresarial de que sean errores.'},
 {asunto:'Grupo seleccionado',cantidad:50,decision:'De 315 elegibles: continuidad hasta julio y mayor número de días con venta.'},
 {asunto:'Existencias comprobadas',cantidad:null,decision:'No disponibles. El saldo calculado no prueba existencias de la empresa.'}];
 table(first,decisions,['asunto','cantidad','decision'],'Preparación académica v1 | Originales conservados. Las decisiones de tratamiento no certifican el significado comercial de las incidencias.');
 table('Productos',p.products,['rango','producto_id','producto','categoria','meses_venta','meses_compra','dias_venta','unidades_vendidas','corte_seleccion'],'Selección con datos hasta el 31/07/2026. Agosto y septiembre no influyen en el orden.');
 table('Incidencias',p.issues,Object.keys(p.issues[0]),'Ubicación y tratamiento de las ocho incidencias. Los importes no se corrigen por inferencia.');
 table('Fuentes',p.source_counts,['archivo','tipo','filas','VENTA','CREDITO','COMPRA','COMPRA_SIN_CARGO_REGISTRADO','CUARENTENA'],'Conteos de las 14 fuentes originales. Las huellas de integridad completas están en manifest.json y en cada registro normalizado.');
}else throw Error('ventas|compras|inventario|control required');
wb.recalculate();
console.log((await wb.inspect({kind:'region',sheetId:first,range:'A4:F7',maxChars:1300,tableMaxCols:6,tableMaxRows:4})).ndjson);
const preview=await wb.render({sheetName:first,range:'A1:F10',scale:1,format:'png'});
await fs.writeFile(new URL(mode+'_preview.png',root),new Uint8Array(await preview.arrayBuffer()));
await (await SpreadsheetFile.exportXlsx(wb)).save(new URL(file,out).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
console.log('SAVED '+file);
