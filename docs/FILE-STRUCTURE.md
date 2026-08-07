# File Structure

## ROMX container

```text
┌──────────────────────────────┐
│ ROM payload                  │  Unmodified standard ROM
├──────────────────────────────┤
│ Metadata JSON                │  Embedded UTF-8 JSON
├──────────────────────────────┤
│ Cover image                  │  Optional PNG
├──────────────────────────────┤
│ ROMX footer                  │  Fixed 128 bytes
└──────────────────────────────┘
```

Readers must use footer offsets and sizes; they must not depend on region order. ROM, metadata, and cover regions must not overlap or cover the footer.
