
export const SCHEMA_ID_TO_NAME: { [key: string]: string } = {
    "01": "DaRoot",
    "02": "DaPermit",
    "03": "DaField",
    "04": "DaFieldSpecific",
    "05": "DaFieldBhl",
    "06": "DaCanRestr",
    "07": "DaCanRestrField",
    "08": "DaFreeRestr",
    "09": "DaFreeRestrField",
    "10": "DaPermitBhl",
    "11": "DaAlternateAddr",
    "12": "DaRemark",
    "13": "DaCheckRegister",
    "14": "DaSurfaceLoc",
    "15": "DaBottomHoleLoc",
};

export const SCHEMA_NAME_TO_ID: { [key: string]: string } = {};
for (const [id, name] of Object.entries(SCHEMA_ID_TO_NAME)) {
    SCHEMA_NAME_TO_ID[name] = id;
}

export const SCHEMAS = Object.keys(SCHEMA_ID_TO_NAME);
