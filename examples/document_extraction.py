"""
Document Extraction
===================

Demonstrates claude-hooks for extracting structured data from unstructured text.
Claude parses invoices into typed Pydantic models.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/document_extraction.py
"""
import asyncio
import os

from pydantic import BaseModel

from claudehooks import HookRouter


class InvoiceData(BaseModel):
    vendor_name: str
    invoice_number: str
    date: str
    total_amount: float
    currency: str
    line_items: list[str]
    payment_due: str


router = HookRouter(
    api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    cache_enabled=True,
)


@router.hook(model="sonnet", fallback="raise")
async def extract_invoice(document_text: str) -> InvoiceData:
    """You are a document extraction system. Parse the invoice text and extract
    all structured fields.

    Extract:
    - vendor_name: the company issuing the invoice
    - invoice_number: the unique invoice identifier
    - date: the invoice date (YYYY-MM-DD format)
    - total_amount: the total amount as a float
    - currency: the currency code (e.g., "USD", "EUR")
    - line_items: list of item descriptions
    - payment_due: the payment due date (YYYY-MM-DD format)

    If a field is not found, use "UNKNOWN" for strings and 0.0 for amounts.
    """
    ...


async def main():
    invoices = [
        """
        INVOICE #INV-2024-0847
        Acme Cloud Services LLC
        Date: March 15, 2024

        Description                     Amount
        ----------------------------------------
        Cloud Hosting (Pro Plan)        $299.00
        Additional Storage (500GB)       $49.99
        SSL Certificate (Annual)         $79.00
        ----------------------------------------
        Subtotal:                       $427.99
        Tax (8.25%):                     $35.31
        TOTAL:                          $463.30

        Payment Due: April 14, 2024
        Currency: USD
        """,
        """
        Invoice: 2024-EU-1923
        From: Berlin Digital GmbH
        Issued: 2024-02-28

        - Web Development Services: EUR 4,500.00
        - UI/UX Design Package: EUR 2,200.00
        - Hosting Setup: EUR 350.00

        Total: EUR 7,050.00
        Due by: 2024-03-30
        """,
    ]

    for doc in invoices:
        result = await extract_invoice(doc.strip())
        print(f"Vendor: {result.vendor_name}")
        print(f"Invoice #: {result.invoice_number}")
        print(f"Date: {result.date}")
        print(f"Total: {result.currency} {result.total_amount:.2f}")
        print(f"Items: {', '.join(result.line_items)}")
        print(f"Due: {result.payment_due}")
        print()

    stats = router.stats()
    print(f"--- Stats: {stats['total_calls']} calls, ${stats['total_cost_usd']:.6f} ---")


if __name__ == "__main__":
    asyncio.run(main())
