-- =============================================================================
-- Dados de vendas fictícios para demonstração do agente de análise
-- Produtos: Software Enterprise, Cloud Platform, Data Analytics,
--           Security Suite, AI Assistant
-- Regiões: Norte, Sul, Sudeste, Nordeste, Centro-Oeste
-- Anos: 2024, 2025 | Trimestres: Q1, Q2, Q3, Q4
-- Nota: AI Assistant tem crescimento acelerado em 2025 (produto novo)
-- =============================================================================

CREATE TABLE IF NOT EXISTS sales (
    id          INTEGER PRIMARY KEY,
    product     TEXT    NOT NULL,
    region      TEXT    NOT NULL,
    quarter     TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    revenue     REAL    NOT NULL,
    units_sold  INTEGER NOT NULL,
    cost        REAL    NOT NULL
);

-- =============================================================================
-- 2024 — Q1
-- =============================================================================
INSERT INTO sales (product, region, quarter, year, revenue, units_sold, cost) VALUES
    ('Software Enterprise', 'Sudeste',      'Q1', 2024, 540000.00, 18, 210000.00),
    ('Software Enterprise', 'Sul',          'Q1', 2024, 320000.00, 11, 125000.00),
    ('Software Enterprise', 'Norte',        'Q1', 2024, 185000.00,  7,  72000.00),
    ('Software Enterprise', 'Nordeste',     'Q1', 2024, 210000.00,  8,  82000.00),
    ('Software Enterprise', 'Centro-Oeste', 'Q1', 2024, 160000.00,  6,  62000.00),

    ('Cloud Platform',      'Sudeste',      'Q1', 2024, 620000.00, 31, 248000.00),
    ('Cloud Platform',      'Sul',          'Q1', 2024, 410000.00, 22, 164000.00),
    ('Cloud Platform',      'Norte',        'Q1', 2024, 230000.00, 12,  92000.00),
    ('Cloud Platform',      'Nordeste',     'Q1', 2024, 275000.00, 14, 110000.00),
    ('Cloud Platform',      'Centro-Oeste', 'Q1', 2024, 195000.00, 10,  78000.00),

    ('Data Analytics',      'Sudeste',      'Q1', 2024, 480000.00, 24, 192000.00),
    ('Data Analytics',      'Sul',          'Q1', 2024, 295000.00, 15, 118000.00),
    ('Data Analytics',      'Norte',        'Q1', 2024, 155000.00,  8,  62000.00),
    ('Data Analytics',      'Nordeste',     'Q1', 2024, 190000.00, 10,  76000.00),
    ('Data Analytics',      'Centro-Oeste', 'Q1', 2024, 140000.00,  7,  56000.00),

    ('Security Suite',      'Sudeste',      'Q1', 2024, 370000.00, 37, 148000.00),
    ('Security Suite',      'Sul',          'Q1', 2024, 245000.00, 25,  98000.00),
    ('Security Suite',      'Norte',        'Q1', 2024, 130000.00, 13,  52000.00),
    ('Security Suite',      'Nordeste',     'Q1', 2024, 160000.00, 16,  64000.00),
    ('Security Suite',      'Centro-Oeste', 'Q1', 2024, 110000.00, 11,  44000.00);

-- =============================================================================
-- 2024 — Q2
-- =============================================================================
INSERT INTO sales (product, region, quarter, year, revenue, units_sold, cost) VALUES
    ('Software Enterprise', 'Sudeste',      'Q2', 2024, 575000.00, 19, 224000.00),
    ('Software Enterprise', 'Sul',          'Q2', 2024, 345000.00, 12, 134000.00),
    ('Software Enterprise', 'Norte',        'Q2', 2024, 200000.00,  8,  78000.00),
    ('Software Enterprise', 'Nordeste',     'Q2', 2024, 228000.00,  9,  89000.00),
    ('Software Enterprise', 'Centro-Oeste', 'Q2', 2024, 172000.00,  7,  67000.00),

    ('Cloud Platform',      'Sudeste',      'Q2', 2024, 680000.00, 34, 272000.00),
    ('Cloud Platform',      'Sul',          'Q2', 2024, 450000.00, 24, 180000.00),
    ('Cloud Platform',      'Norte',        'Q2', 2024, 255000.00, 14, 102000.00),
    ('Cloud Platform',      'Nordeste',     'Q2', 2024, 310000.00, 17, 124000.00),
    ('Cloud Platform',      'Centro-Oeste', 'Q2', 2024, 220000.00, 12,  88000.00),

    ('Data Analytics',      'Sudeste',      'Q2', 2024, 515000.00, 26, 206000.00),
    ('Data Analytics',      'Sul',          'Q2', 2024, 320000.00, 16, 128000.00),
    ('Data Analytics',      'Norte',        'Q2', 2024, 170000.00,  9,  68000.00),
    ('Data Analytics',      'Nordeste',     'Q2', 2024, 205000.00, 11,  82000.00),
    ('Data Analytics',      'Centro-Oeste', 'Q2', 2024, 152000.00,  8,  61000.00),

    ('Security Suite',      'Sudeste',      'Q2', 2024, 395000.00, 40, 158000.00),
    ('Security Suite',      'Sul',          'Q2', 2024, 265000.00, 27, 106000.00),
    ('Security Suite',      'Norte',        'Q2', 2024, 140000.00, 14,  56000.00),
    ('Security Suite',      'Nordeste',     'Q2', 2024, 175000.00, 18,  70000.00),
    ('Security Suite',      'Centro-Oeste', 'Q2', 2024, 120000.00, 12,  48000.00),

    -- AI Assistant: lançamento tímido em Q2/2024
    ('AI Assistant',        'Sudeste',      'Q2', 2024,  85000.00,  5,  42000.00),
    ('AI Assistant',        'Sul',          'Q2', 2024,  48000.00,  3,  24000.00),
    ('AI Assistant',        'Nordeste',     'Q2', 2024,  32000.00,  2,  16000.00);

-- =============================================================================
-- 2024 — Q3
-- =============================================================================
INSERT INTO sales (product, region, quarter, year, revenue, units_sold, cost) VALUES
    ('Software Enterprise', 'Sudeste',      'Q3', 2024, 610000.00, 20, 238000.00),
    ('Software Enterprise', 'Sul',          'Q3', 2024, 370000.00, 13, 144000.00),
    ('Software Enterprise', 'Norte',        'Q3', 2024, 215000.00,  8,  84000.00),
    ('Software Enterprise', 'Nordeste',     'Q3', 2024, 248000.00, 10,  97000.00),
    ('Software Enterprise', 'Centro-Oeste', 'Q3', 2024, 185000.00,  7,  72000.00),

    ('Cloud Platform',      'Sudeste',      'Q3', 2024, 730000.00, 37, 292000.00),
    ('Cloud Platform',      'Sul',          'Q3', 2024, 490000.00, 26, 196000.00),
    ('Cloud Platform',      'Norte',        'Q3', 2024, 275000.00, 15, 110000.00),
    ('Cloud Platform',      'Nordeste',     'Q3', 2024, 340000.00, 19, 136000.00),
    ('Cloud Platform',      'Centro-Oeste', 'Q3', 2024, 245000.00, 13,  98000.00),

    ('Data Analytics',      'Sudeste',      'Q3', 2024, 555000.00, 28, 222000.00),
    ('Data Analytics',      'Sul',          'Q3', 2024, 345000.00, 17, 138000.00),
    ('Data Analytics',      'Norte',        'Q3', 2024, 185000.00, 10,  74000.00),
    ('Data Analytics',      'Nordeste',     'Q3', 2024, 225000.00, 12,  90000.00),
    ('Data Analytics',      'Centro-Oeste', 'Q3', 2024, 165000.00,  9,  66000.00),

    ('Security Suite',      'Sudeste',      'Q3', 2024, 420000.00, 42, 168000.00),
    ('Security Suite',      'Sul',          'Q3', 2024, 285000.00, 29, 114000.00),
    ('Security Suite',      'Norte',        'Q3', 2024, 152000.00, 15,  61000.00),
    ('Security Suite',      'Nordeste',     'Q3', 2024, 188000.00, 19,  75000.00),
    ('Security Suite',      'Centro-Oeste', 'Q3', 2024, 130000.00, 13,  52000.00),

    -- AI Assistant: tração crescente no segundo semestre de 2024
    ('AI Assistant',        'Sudeste',      'Q3', 2024, 165000.00,  9,  74000.00),
    ('AI Assistant',        'Sul',          'Q3', 2024,  98000.00,  6,  44000.00),
    ('AI Assistant',        'Norte',        'Q3', 2024,  55000.00,  3,  25000.00),
    ('AI Assistant',        'Nordeste',     'Q3', 2024,  72000.00,  4,  32000.00),
    ('AI Assistant',        'Centro-Oeste', 'Q3', 2024,  43000.00,  3,  19000.00);

-- =============================================================================
-- 2024 — Q4
-- =============================================================================
INSERT INTO sales (product, region, quarter, year, revenue, units_sold, cost) VALUES
    ('Software Enterprise', 'Sudeste',      'Q4', 2024, 650000.00, 22, 253000.00),
    ('Software Enterprise', 'Sul',          'Q4', 2024, 395000.00, 14, 154000.00),
    ('Software Enterprise', 'Norte',        'Q4', 2024, 228000.00,  9,  89000.00),
    ('Software Enterprise', 'Nordeste',     'Q4', 2024, 265000.00, 10, 103000.00),
    ('Software Enterprise', 'Centro-Oeste', 'Q4', 2024, 198000.00,  8,  77000.00),

    ('Cloud Platform',      'Sudeste',      'Q4', 2024, 790000.00, 40, 316000.00),
    ('Cloud Platform',      'Sul',          'Q4', 2024, 530000.00, 28, 212000.00),
    ('Cloud Platform',      'Norte',        'Q4', 2024, 298000.00, 16, 119000.00),
    ('Cloud Platform',      'Nordeste',     'Q4', 2024, 365000.00, 20, 146000.00),
    ('Cloud Platform',      'Centro-Oeste', 'Q4', 2024, 265000.00, 14, 106000.00),

    ('Data Analytics',      'Sudeste',      'Q4', 2024, 595000.00, 30, 238000.00),
    ('Data Analytics',      'Sul',          'Q4', 2024, 370000.00, 19, 148000.00),
    ('Data Analytics',      'Norte',        'Q4', 2024, 198000.00, 10,  79000.00),
    ('Data Analytics',      'Nordeste',     'Q4', 2024, 242000.00, 13,  97000.00),
    ('Data Analytics',      'Centro-Oeste', 'Q4', 2024, 178000.00,  9,  71000.00),

    ('Security Suite',      'Sudeste',      'Q4', 2024, 455000.00, 46, 182000.00),
    ('Security Suite',      'Sul',          'Q4', 2024, 308000.00, 31, 123000.00),
    ('Security Suite',      'Norte',        'Q4', 2024, 165000.00, 17,  66000.00),
    ('Security Suite',      'Nordeste',     'Q4', 2024, 202000.00, 20,  81000.00),
    ('Security Suite',      'Centro-Oeste', 'Q4', 2024, 142000.00, 14,  57000.00),

    -- AI Assistant: forte fechamento de 2024, produto ganha mercado
    ('AI Assistant',        'Sudeste',      'Q4', 2024, 310000.00, 16, 124000.00),
    ('AI Assistant',        'Sul',          'Q4', 2024, 185000.00, 10,  74000.00),
    ('AI Assistant',        'Norte',        'Q4', 2024, 105000.00,  6,  42000.00),
    ('AI Assistant',        'Nordeste',     'Q4', 2024, 138000.00,  8,  55000.00),
    ('AI Assistant',        'Centro-Oeste', 'Q4', 2024,  85000.00,  5,  34000.00);

-- =============================================================================
-- 2025 — Q1
-- =============================================================================
INSERT INTO sales (product, region, quarter, year, revenue, units_sold, cost) VALUES
    ('Software Enterprise', 'Sudeste',      'Q1', 2025, 690000.00, 23, 269000.00),
    ('Software Enterprise', 'Sul',          'Q1', 2025, 418000.00, 15, 163000.00),
    ('Software Enterprise', 'Norte',        'Q1', 2025, 242000.00, 10,  94000.00),
    ('Software Enterprise', 'Nordeste',     'Q1', 2025, 280000.00, 11, 109000.00),
    ('Software Enterprise', 'Centro-Oeste', 'Q1', 2025, 210000.00,  8,  82000.00),

    ('Cloud Platform',      'Sudeste',      'Q1', 2025, 855000.00, 43, 342000.00),
    ('Cloud Platform',      'Sul',          'Q1', 2025, 575000.00, 31, 230000.00),
    ('Cloud Platform',      'Norte',        'Q1', 2025, 325000.00, 18, 130000.00),
    ('Cloud Platform',      'Nordeste',     'Q1', 2025, 398000.00, 22, 159000.00),
    ('Cloud Platform',      'Centro-Oeste', 'Q1', 2025, 288000.00, 16, 115000.00),

    ('Data Analytics',      'Sudeste',      'Q1', 2025, 635000.00, 32, 254000.00),
    ('Data Analytics',      'Sul',          'Q1', 2025, 395000.00, 20, 158000.00),
    ('Data Analytics',      'Norte',        'Q1', 2025, 212000.00, 11,  85000.00),
    ('Data Analytics',      'Nordeste',     'Q1', 2025, 260000.00, 14, 104000.00),
    ('Data Analytics',      'Centro-Oeste', 'Q1', 2025, 190000.00, 10,  76000.00),

    ('Security Suite',      'Sudeste',      'Q1', 2025, 488000.00, 49, 195000.00),
    ('Security Suite',      'Sul',          'Q1', 2025, 332000.00, 34, 133000.00),
    ('Security Suite',      'Norte',        'Q1', 2025, 178000.00, 18,  71000.00),
    ('Security Suite',      'Nordeste',     'Q1', 2025, 218000.00, 22,  87000.00),
    ('Security Suite',      'Centro-Oeste', 'Q1', 2025, 154000.00, 15,  62000.00),

    -- AI Assistant: explosão de crescimento em 2025
    ('AI Assistant',        'Sudeste',      'Q1', 2025, 580000.00, 29, 203000.00),
    ('AI Assistant',        'Sul',          'Q1', 2025, 348000.00, 18, 122000.00),
    ('AI Assistant',        'Norte',        'Q1', 2025, 198000.00, 10,  69000.00),
    ('AI Assistant',        'Nordeste',     'Q1', 2025, 260000.00, 13,  91000.00),
    ('AI Assistant',        'Centro-Oeste', 'Q1', 2025, 160000.00,  8,  56000.00);

-- =============================================================================
-- 2025 — Q2
-- =============================================================================
INSERT INTO sales (product, region, quarter, year, revenue, units_sold, cost) VALUES
    ('Software Enterprise', 'Sudeste',      'Q2', 2025, 725000.00, 24, 283000.00),
    ('Software Enterprise', 'Sul',          'Q2', 2025, 440000.00, 16, 172000.00),
    ('Software Enterprise', 'Norte',        'Q2', 2025, 255000.00, 10,  99000.00),
    ('Software Enterprise', 'Nordeste',     'Q2', 2025, 298000.00, 12, 116000.00),
    ('Software Enterprise', 'Centro-Oeste', 'Q2', 2025, 222000.00,  9,  87000.00),

    ('Cloud Platform',      'Sudeste',      'Q2', 2025, 925000.00, 47, 370000.00),
    ('Cloud Platform',      'Sul',          'Q2', 2025, 622000.00, 34, 249000.00),
    ('Cloud Platform',      'Norte',        'Q2', 2025, 352000.00, 19, 141000.00),
    ('Cloud Platform',      'Nordeste',     'Q2', 2025, 430000.00, 24, 172000.00),
    ('Cloud Platform',      'Centro-Oeste', 'Q2', 2025, 312000.00, 17, 125000.00),

    ('Data Analytics',      'Sudeste',      'Q2', 2025, 682000.00, 34, 273000.00),
    ('Data Analytics',      'Sul',          'Q2', 2025, 425000.00, 22, 170000.00),
    ('Data Analytics',      'Norte',        'Q2', 2025, 228000.00, 12,  91000.00),
    ('Data Analytics',      'Nordeste',     'Q2', 2025, 280000.00, 15, 112000.00),
    ('Data Analytics',      'Centro-Oeste', 'Q2', 2025, 205000.00, 11,  82000.00),

    ('Security Suite',      'Sudeste',      'Q2', 2025, 522000.00, 52, 209000.00),
    ('Security Suite',      'Sul',          'Q2', 2025, 355000.00, 36, 142000.00),
    ('Security Suite',      'Norte',        'Q2', 2025, 192000.00, 19,  77000.00),
    ('Security Suite',      'Nordeste',     'Q2', 2025, 235000.00, 24,  94000.00),
    ('Security Suite',      'Centro-Oeste', 'Q2', 2025, 165000.00, 17,  66000.00),

    -- AI Assistant: dominando pauta de investimentos em 2025
    ('AI Assistant',        'Sudeste',      'Q2', 2025, 920000.00, 46, 322000.00),
    ('AI Assistant',        'Sul',          'Q2', 2025, 552000.00, 28, 193000.00),
    ('AI Assistant',        'Norte',        'Q2', 2025, 315000.00, 16, 110000.00),
    ('AI Assistant',        'Nordeste',     'Q2', 2025, 415000.00, 21, 145000.00),
    ('AI Assistant',        'Centro-Oeste', 'Q2', 2025, 255000.00, 13,  89000.00);

-- =============================================================================
-- 2025 — Q3
-- =============================================================================
INSERT INTO sales (product, region, quarter, year, revenue, units_sold, cost) VALUES
    ('Software Enterprise', 'Sudeste',      'Q3', 2025, 762000.00, 25, 297000.00),
    ('Software Enterprise', 'Sul',          'Q3', 2025, 462000.00, 17, 180000.00),
    ('Software Enterprise', 'Norte',        'Q3', 2025, 268000.00, 11, 105000.00),
    ('Software Enterprise', 'Nordeste',     'Q3', 2025, 312000.00, 13, 122000.00),
    ('Software Enterprise', 'Centro-Oeste', 'Q3', 2025, 234000.00,  9,  91000.00),

    ('Cloud Platform',      'Sudeste',      'Q3', 2025, 998000.00, 50, 399000.00),
    ('Cloud Platform',      'Sul',          'Q3', 2025, 672000.00, 36, 269000.00),
    ('Cloud Platform',      'Norte',        'Q3', 2025, 382000.00, 21, 153000.00),
    ('Cloud Platform',      'Nordeste',     'Q3', 2025, 465000.00, 26, 186000.00),
    ('Cloud Platform',      'Centro-Oeste', 'Q3', 2025, 338000.00, 18, 135000.00),

    ('Data Analytics',      'Sudeste',      'Q3', 2025, 728000.00, 36, 291000.00),
    ('Data Analytics',      'Sul',          'Q3', 2025, 455000.00, 23, 182000.00),
    ('Data Analytics',      'Norte',        'Q3', 2025, 245000.00, 13,  98000.00),
    ('Data Analytics',      'Nordeste',     'Q3', 2025, 302000.00, 16, 121000.00),
    ('Data Analytics',      'Centro-Oeste', 'Q3', 2025, 220000.00, 12,  88000.00),

    ('Security Suite',      'Sudeste',      'Q3', 2025, 558000.00, 56, 223000.00),
    ('Security Suite',      'Sul',          'Q3', 2025, 380000.00, 38, 152000.00),
    ('Security Suite',      'Norte',        'Q3', 2025, 205000.00, 21,  82000.00),
    ('Security Suite',      'Nordeste',     'Q3', 2025, 252000.00, 25, 101000.00),
    ('Security Suite',      'Centro-Oeste', 'Q3', 2025, 178000.00, 18,  71000.00),

    -- AI Assistant: crescimento explosivo sustentado em 2025
    ('AI Assistant',        'Sudeste',      'Q3', 2025, 1380000.00, 69, 483000.00),
    ('AI Assistant',        'Sul',          'Q3', 2025,  828000.00, 42, 290000.00),
    ('AI Assistant',        'Norte',        'Q3', 2025,  473000.00, 24, 166000.00),
    ('AI Assistant',        'Nordeste',     'Q3', 2025,  623000.00, 32, 218000.00),
    ('AI Assistant',        'Centro-Oeste', 'Q3', 2025,  383000.00, 19, 134000.00);

-- =============================================================================
-- 2025 — Q4
-- =============================================================================
INSERT INTO sales (product, region, quarter, year, revenue, units_sold, cost) VALUES
    ('Software Enterprise', 'Sudeste',      'Q4', 2025, 820000.00, 27, 320000.00),
    ('Software Enterprise', 'Sul',          'Q4', 2025, 498000.00, 18, 194000.00),
    ('Software Enterprise', 'Norte',        'Q4', 2025, 288000.00, 12, 112000.00),
    ('Software Enterprise', 'Nordeste',     'Q4', 2025, 338000.00, 14, 132000.00),
    ('Software Enterprise', 'Centro-Oeste', 'Q4', 2025, 252000.00, 10,  98000.00),

    ('Cloud Platform',      'Sudeste',      'Q4', 2025, 1085000.00, 54, 434000.00),
    ('Cloud Platform',      'Sul',          'Q4', 2025,  730000.00, 39, 292000.00),
    ('Cloud Platform',      'Norte',        'Q4', 2025,  415000.00, 23, 166000.00),
    ('Cloud Platform',      'Nordeste',     'Q4', 2025,  505000.00, 28, 202000.00),
    ('Cloud Platform',      'Centro-Oeste', 'Q4', 2025,  368000.00, 20, 147000.00),

    ('Data Analytics',      'Sudeste',      'Q4', 2025, 788000.00, 39, 315000.00),
    ('Data Analytics',      'Sul',          'Q4', 2025, 492000.00, 25, 197000.00),
    ('Data Analytics',      'Norte',        'Q4', 2025, 265000.00, 14, 106000.00),
    ('Data Analytics',      'Nordeste',     'Q4', 2025, 325000.00, 17, 130000.00),
    ('Data Analytics',      'Centro-Oeste', 'Q4', 2025, 238000.00, 12,  95000.00),

    ('Security Suite',      'Sudeste',      'Q4', 2025, 608000.00, 61, 243000.00),
    ('Security Suite',      'Sul',          'Q4', 2025, 415000.00, 42, 166000.00),
    ('Security Suite',      'Norte',        'Q4', 2025, 225000.00, 23,  90000.00),
    ('Security Suite',      'Nordeste',     'Q4', 2025, 275000.00, 28, 110000.00),
    ('Security Suite',      'Centro-Oeste', 'Q4', 2025, 195000.00, 20,  78000.00),

    -- AI Assistant: pico histórico no fechamento de 2025
    ('AI Assistant',        'Sudeste',      'Q4', 2025, 1950000.00, 97, 683000.00),
    ('AI Assistant',        'Sul',          'Q4', 2025, 1170000.00, 59, 410000.00),
    ('AI Assistant',        'Norte',        'Q4', 2025,  670000.00, 34, 235000.00),
    ('AI Assistant',        'Nordeste',     'Q4', 2025,  882000.00, 44, 309000.00),
    ('AI Assistant',        'Centro-Oeste', 'Q4', 2025,  542000.00, 27, 190000.00);

-- =============================================================================
-- Índices para consultas analíticas eficientes
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_sales_year_quarter ON sales (year, quarter);
CREATE INDEX IF NOT EXISTS idx_sales_product       ON sales (product);
CREATE INDEX IF NOT EXISTS idx_sales_region        ON sales (region);
CREATE INDEX IF NOT EXISTS idx_sales_year          ON sales (year);
