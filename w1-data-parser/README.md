# w1-data-parser

A robust and efficient TypeScript parser for Texas Railroad Commission (RRC) W-1 data files. This library processes fixed-width text files containing well, permit, and production data, converting them into structured, easy-to-use JSON objects.

## Features

-   **Full Schema Support**: Parses all standard segments including Root, Permit, Field, Field Specific, BHL, Restrictions, Alternate Address, Remarks, Check Register, and Location data.
-   **Hierarchical Grouping**: Automatically groups related records (e.g., permits, locations) under their parent root record.
-   **TypeScript Support**: Fully typed models and schemas for excellent developer experience.
-   **Optional Transformations**: Can automatically decode standard RRC codes (County, Well Status, etc.) into human-readable strings.
-   **Flexible Filtering**: Parse only the specific record types you need for better performance.

## Installation

```bash
npm install w1-data-parser
```

## Usage

### Basic Parsing

The core of the library is the `W1Parser` class. It reads a file path and returns a list of `W1RecordGroup` objects.

```typescript
import { W1Parser } from 'w1-data-parser';

async function main() {
    const parser = new W1Parser();
    const records = await parser.parseFile('./path/to/w1_data.dat');

    console.log(`Parsed ${records.length} root records.`);

    // Access data hierarchically
    const firstGroup = records[0];
    
    // Root record (Segment 01)
    console.log('Lease Name:', firstGroup["01"]?.lease_name);

    // Permit record (Segment 02)
    console.log('API Number:', firstGroup["02"]?.api_number);

    // Some segments are lists (e.g., Segment 12 Remarks)
    if (firstGroup["12"]) {
        firstGroup["12"].forEach(remark => {
            console.log('Remark:', remark.remark_line);
        });
    }
}

main();
```

### Filtering Schemas

If you only care about specific data segments (e.g., just the basic permit info), you can filter the parser to skip other lines. This can significantly speed up processing large files.

```typescript
// Parse only Root (01) and Permit (02) records
const records = await parser.parseFile('./data.dat', ['01', '02']);
```

### Code Transformation

The RRC data uses many code values (e.g., County Codes, Well Status). The parser can optionally transform these into their text descriptions during parsing.

```typescript
// Enable code transformation (3rd argument)
const records = await parser.parseFile('./data.dat', undefined, true);

// Now accessing fields returns the description instead of the code
// e.g., '109' becomes 'CULBERSON'
console.log('County:', records[0]["01"]?.county_code); 
```

### JSON Serialization

For use in web APIs (e.g., Next.js), you often need plain objects instead of class instances. `W1RecordGroup` supports `JSON.stringify()` directly, or you can use the `toObject()` helper.

```typescript
import { W1Parser } from 'w1-data-parser';

const parser = new W1Parser();
const records = await parser.parseFile('./data.dat');

// Automatic serialization works
const jsonString = JSON.stringify(records);

// Or get a plain object explicitly (useful for Next.js props)
const plainObject = records[0].toObject();
```

## Development & Publishing

### Build
To compile the TypeScript source to JavaScript into the `dist` directory:

```bash
npm run build
```

### Test
Run the test suite using Jest:

```bash
npm test
```

### Publish to npm
1.  Update the version in `package.json`.
2.  Run the build to ensure the latest code is compiled.
3.  Publish using `npm publish`.

```bash
npm run build
npm publish
```

Make sure you are logged in to npm (`npm login`) before publishing.

## License

ISC
