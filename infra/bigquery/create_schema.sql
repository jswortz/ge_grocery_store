-- ============================================================
-- Star Schema DDL for Grocery Retail Analytics
-- Dataset: ge_grocery_demo
-- ============================================================
-- Run with: bq query --use_legacy_sql=false < create_schema.sql
-- Or execute individual statements via BigQuery console.
--
-- NOTE: Store names and brands are generic. Update config/settings.yaml
-- to customize for specific retail clients.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS `wortz-project-352116.ge_grocery_demo`
OPTIONS (
  location = 'US',
  description = 'Grocery retail star schema for Gemini Enterprise workshop'
);

-- Dimension: Stores
CREATE OR REPLACE TABLE `wortz-project-352116.ge_grocery_demo.dim_store` (
  store_id       INT64 NOT NULL,
  store_name     STRING NOT NULL,
  city           STRING NOT NULL,
  state          STRING NOT NULL,
  zip_code       STRING NOT NULL,
  square_feet    INT64,
  open_date      DATE
);

-- Dimension: Products (with multi-modal enrichment columns)
CREATE OR REPLACE TABLE `wortz-project-352116.ge_grocery_demo.dim_product` (
  product_id     INT64 NOT NULL,
  product_name   STRING NOT NULL,
  category       STRING NOT NULL,
  subcategory    STRING,
  brand          STRING,
  unit_price     NUMERIC NOT NULL,
  unit_cost      NUMERIC NOT NULL,
  image_uri      STRING,
  description    STRING
);

-- Dimension: Employees (with role hierarchy)
CREATE OR REPLACE TABLE `wortz-project-352116.ge_grocery_demo.dim_employee` (
  employee_id    INT64 NOT NULL,
  first_name     STRING NOT NULL,
  last_name      STRING NOT NULL,
  role           STRING NOT NULL,
  store_id       INT64 NOT NULL,
  hire_date      DATE
);

-- Dimension: Customers (loyalty program)
CREATE OR REPLACE TABLE `wortz-project-352116.ge_grocery_demo.dim_customer` (
  customer_id    INT64 NOT NULL,
  first_name     STRING NOT NULL,
  last_name      STRING NOT NULL,
  email          STRING,
  phone          STRING,
  loyalty_tier   STRING NOT NULL,
  home_store_id  INT64 NOT NULL,
  signup_date    DATE NOT NULL,
  points_balance INT64 NOT NULL
);

-- Fact: Transactions
CREATE OR REPLACE TABLE `wortz-project-352116.ge_grocery_demo.fact_transactions` (
  transaction_id   INT64 NOT NULL,
  transaction_ts   TIMESTAMP NOT NULL,
  store_id         INT64 NOT NULL,
  employee_id      INT64 NOT NULL,
  product_id       INT64 NOT NULL,
  quantity         INT64 NOT NULL,
  unit_price       NUMERIC NOT NULL,
  total_amount     NUMERIC NOT NULL,
  payment_method   STRING NOT NULL,
  customer_id      INT64
);
