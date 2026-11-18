import {CONFIG} from "./config.js";
export function field(row,kind,key){const aliases=CONFIG.aliases[kind]?.[key]||[key];for(const a of aliases){if(row?.[a]!==undefined&&row[a]!==null&&row[a]!=="")return row[a];}return null;}
export function num(v){if(v==null||v==="")return null;const n=Number(String(v).replace(/,/g,""));return Number.isFinite(n)?n:null;}
export function periodOf(row,kind="eia"){const p=field(row,kind,"period");if(p)return String(p).slice(0,7);const y=field(row,kind,"year"),m=field(row,kind,"month");if(y&&m)return `${y}-${String(m).padStart(2,"0")}`;const ts=field(row,kind,"timestamp");if(ts)return String(ts).slice(0,7);return "";}
export function stateOf(row,kind="eia"){return String(field(row,kind,"state")||"").toUpperCase();}
export function stateLabel(code){return ({CO:"Colorado",NY:"Nueva York",DC:"Distrito de Columbia"})[code]||code;}
