# PRD – BidCardAgent (InstaBids)

## 1. Purpose
Standardizes project requests into structured formats that contractors can easily understand and bid on.

## 2. Key Capabilities

| Capability             | Details                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **Standardization**    | Convert free-form project descriptions into structured bid cards        |
| **Detail Extraction**  | Extract key project details like materials, dimensions, and requirements|
| **Classification**     | Categorize projects by trade, complexity, and estimated effort          |
| **Format Conversion**  | Present information in contractor-friendly formats                      |
| **Data Enrichment**    | Add relevant context and specifications to improve bid accuracy         |

## 3. Integration Points

- Receives project data from HomeownerAgent
- Outputs standardized bid cards for ContractorAgent
- Stores structured data in Supabase
