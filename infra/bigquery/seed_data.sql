-- ============================================================
-- Seed Data for Grocery Retail Star Schema
-- Dataset: ge_grocery_demo
-- ============================================================
-- Generic retailer names — no client-specific branding.
-- ============================================================

-- Stores (3 locations)
INSERT INTO `wortz-project-352116.ge_grocery_demo.dim_store`
  (store_id, store_name, city, state, zip_code, square_feet, open_date)
VALUES
  (1, 'Downtown Market',  'Austin',      'TX', '78701', 85000, '2015-03-12'),
  (2, 'Westside Market',  'San Antonio', 'TX', '78204', 62000, '2008-07-01'),
  (3, 'Lakefront Market', 'Houston',     'TX', '77006', 74000, '2019-11-15');

-- Products (20 items across 5 categories, generic brands)
INSERT INTO `wortz-project-352116.ge_grocery_demo.dim_product`
  (product_id, product_name, category, subcategory, brand, unit_price, unit_cost, image_uri, description)
VALUES
  -- Produce
  (101, 'Bananas (1 lb)',          'Produce',    'Fruit',           'Farm Fresh',    0.59, 0.25, NULL, 'Ripe yellow bananas, sold by the pound'),
  (102, 'Avocados (each)',         'Produce',    'Fruit',           'Green Valley',  1.29, 0.60, NULL, 'Hass avocados, ready to eat'),
  (103, 'Roma Tomatoes (1 lb)',    'Produce',    'Vegetable',       'Farm Fresh',    1.99, 0.90, NULL, 'Vine-ripened roma tomatoes'),
  (104, 'Baby Spinach (5 oz)',     'Produce',    'Vegetable',       'Organics',      3.49, 1.80, NULL, 'Pre-washed organic baby spinach'),
  -- Dairy
  (201, 'Whole Milk (1 gal)',      'Dairy',      'Milk',            'Valley Dairy',  3.79, 2.10, NULL, 'Whole vitamin D milk, one gallon'),
  (202, 'Large Eggs (dozen)',      'Dairy',      'Eggs',            'Country Farm',  2.99, 1.50, NULL, 'Grade A large eggs, 12 count'),
  (203, 'Shredded Cheddar (8 oz)', 'Dairy',      'Cheese',          'Valley Dairy',  3.29, 1.75, NULL, 'Sharp cheddar, finely shredded'),
  (204, 'Greek Yogurt (32 oz)',    'Dairy',      'Yogurt',          'Valley Dairy',  5.49, 2.80, NULL, 'Plain nonfat Greek yogurt'),
  -- Bakery
  (301, 'White Bread Loaf',        'Bakery',     'Bread',           'Golden Grain',  2.49, 1.10, NULL, 'Classic white sandwich bread'),
  (302, 'Flour Tortillas (10 ct)', 'Bakery',     'Tortillas',       'Casa Grande',   2.19, 0.90, NULL, 'Soft flour tortillas, 10 count'),
  (303, 'Hamburger Buns (8 ct)',   'Bakery',     'Bread',           'Golden Grain',  2.99, 1.30, NULL, 'Sesame seed hamburger buns'),
  (304, 'Nano Banana Pro Bar',     'Bakery',     'Specialty',       'Nano Banana',   4.99, 2.20, NULL, 'High-protein banana bread bar with adaptogens'),
  -- Meat
  (401, 'Ground Beef 80/20 (1 lb)','Meat',       'Beef',            'Prairie Ranch', 5.99, 3.50, NULL, '80% lean ground beef, one pound'),
  (402, 'Chicken Breast (1 lb)',   'Meat',       'Poultry',         'Prairie Ranch', 3.99, 2.20, NULL, 'Boneless skinless chicken breast'),
  (403, 'Pork Chops (1 lb)',       'Meat',       'Pork',            'Prairie Ranch', 4.49, 2.50, NULL, 'Center-cut bone-in pork chops'),
  (404, 'Salmon Fillet (8 oz)',    'Meat',       'Seafood',         'Ocean Catch',   8.99, 5.00, NULL, 'Fresh Atlantic salmon fillet'),
  -- Beverages
  (501, 'Sparkling Water (12 oz)', 'Beverages',  'Sparkling Water', 'Crystal Springs',1.49, 0.60, NULL, 'Naturally carbonated mineral water'),
  (502, 'Cola (2 L)',              'Beverages',  'Soda',            'Classic Cola',  2.29, 1.10, NULL, 'Classic cola, 2 liter bottle'),
  (503, 'Orange Juice (64 oz)',    'Beverages',  'Juice',           'Sunrise Grove', 4.99, 2.50, NULL, 'Not from concentrate, 100% pure OJ'),
  (504, 'Cold Brew Coffee (12 oz)','Beverages',  'Coffee',          'Morning Peak',  3.99, 1.80, NULL, 'Ready-to-drink cold brew, unsweetened');

-- Employees (15 across 3 stores, with role hierarchy)
INSERT INTO `wortz-project-352116.ge_grocery_demo.dim_employee`
  (employee_id, first_name, last_name, role, store_id, hire_date)
VALUES
  -- Store 1: Downtown Market
  (1001, 'Maria',   'Garcia',     'Store Manager',      1, '2016-04-01'),
  (1002, 'James',   'Wilson',     'Department Manager', 1, '2018-09-15'),
  (1003, 'Priya',   'Patel',      'Cashier',            1, '2020-06-15'),
  (1004, 'Carlos',  'Hernandez',  'Cashier',            1, '2021-01-10'),
  (1005, 'Aisha',   'Johnson',    'Stock Clerk',        1, '2022-08-20'),
  -- Store 2: Westside Market
  (2001, 'Robert',  'Chen',       'Store Manager',      2, '2010-02-14'),
  (2002, 'Lisa',    'Thompson',   'Department Manager', 2, '2015-06-01'),
  (2003, 'David',   'Kim',        'Cashier',            2, '2019-03-22'),
  (2004, 'Marco',   'Rodriguez',  'Cashier',            2, '2021-11-01'),
  (2005, 'Sarah',   'Mitchell',   'Stock Clerk',        2, '2023-01-15'),
  -- Store 3: Lakefront Market
  (3001, 'Angela',  'Washington', 'Store Manager',      3, '2019-11-20'),
  (3002, 'Michael', 'O''Brien',   'Department Manager', 3, '2020-05-10'),
  (3003, 'Jessica', 'Nguyen',     'Cashier',            3, '2021-07-08'),
  (3004, 'Tyler',   'Brooks',     'Cashier',            3, '2022-04-15'),
  (3005, 'Fatima',  'Ali',        'Stock Clerk',        3, '2023-06-01');

-- Customers (40 with loyalty tiers)
INSERT INTO `wortz-project-352116.ge_grocery_demo.dim_customer`
  (customer_id, first_name, last_name, email, phone, loyalty_tier, home_store_id, signup_date, points_balance)
VALUES
  (5001, 'Jennifer', 'Adams',     'j.adams@email.com',    '512-555-0101', 'Gold',     1, '2020-01-15', 4500),
  (5002, 'William',  'Baker',     'w.baker@email.com',    '512-555-0102', 'Silver',   1, '2020-03-22', 2100),
  (5003, 'Patricia', 'Clark',     'p.clark@email.com',    '512-555-0103', 'Bronze',   1, '2021-06-10', 800),
  (5004, 'Richard',  'Davis',     'r.davis@email.com',    '512-555-0104', 'Gold',     1, '2019-11-05', 6200),
  (5005, 'Linda',    'Evans',     'l.evans@email.com',    '512-555-0105', 'Silver',   1, '2021-02-28', 1900),
  (5006, 'Charles',  'Foster',    'c.foster@email.com',   '512-555-0106', 'Bronze',   1, '2022-08-14', 450),
  (5007, 'Barbara',  'Green',     'b.green@email.com',    '512-555-0107', 'Gold',     1, '2018-07-20', 7800),
  (5008, 'Joseph',   'Harris',    'j.harris@email.com',   '512-555-0108', 'Silver',   1, '2020-12-01', 3200),
  (5009, 'Susan',    'Irving',    's.irving@email.com',   '512-555-0109', 'Bronze',   1, '2023-01-05', 200),
  (5010, 'Thomas',   'Jackson',   't.jackson@email.com',  '512-555-0110', 'Silver',   1, '2021-09-17', 1500),
  (5011, 'Margaret', 'Kelly',     'm.kelly@email.com',    '210-555-0201', 'Gold',     2, '2019-04-12', 5100),
  (5012, 'Daniel',   'Lopez',     'd.lopez@email.com',    '210-555-0202', 'Silver',   2, '2020-06-30', 2800),
  (5013, 'Dorothy',  'Martin',    'd.martin@email.com',   '210-555-0203', 'Bronze',   2, '2021-10-22', 600),
  (5014, 'Paul',     'Nelson',    'p.nelson@email.com',   '210-555-0204', 'Gold',     2, '2017-12-08', 9200),
  (5015, 'Nancy',    'Ortiz',     'n.ortiz@email.com',    '210-555-0205', 'Silver',   2, '2020-02-14', 3500),
  (5016, 'Mark',     'Perez',     'm.perez@email.com',    '210-555-0206', 'Bronze',   2, '2022-05-19', 350),
  (5017, 'Betty',    'Quinn',     'b.quinn@email.com',    '210-555-0207', 'Gold',     2, '2019-08-25', 6800),
  (5018, 'Steven',   'Rivera',    's.rivera@email.com',   '210-555-0208', 'Silver',   2, '2021-01-30', 2200),
  (5019, 'Helen',    'Scott',     'h.scott@email.com',    '210-555-0209', 'Bronze',   2, '2023-03-11', 150),
  (5020, 'Andrew',   'Torres',    'a.torres@email.com',   '210-555-0210', 'Silver',   2, '2020-09-06', 1800),
  (5021, 'Sandra',   'Underwood', 's.underwood@email.com','713-555-0301', 'Gold',     3, '2020-01-20', 4200),
  (5022, 'Kevin',    'Vasquez',   'k.vasquez@email.com',  '713-555-0302', 'Silver',   3, '2020-07-15', 2600),
  (5023, 'Donna',    'Wallace',   'd.wallace@email.com',  '713-555-0303', 'Bronze',   3, '2021-04-08', 700),
  (5024, 'Brian',    'Xiong',     'b.xiong@email.com',    '713-555-0304', 'Gold',     3, '2019-12-12', 5800),
  (5025, 'Carol',    'Young',     'c.young@email.com',    '713-555-0305', 'Silver',   3, '2021-08-30', 1700),
  (5026, 'Edward',   'Zhang',     'e.zhang@email.com',    '713-555-0306', 'Bronze',   3, '2022-11-02', 300),
  (5027, 'Ruth',     'Anderson',  'r.anderson@email.com', '713-555-0307', 'Gold',     3, '2020-03-18', 7100),
  (5028, 'George',   'Brown',     'g.brown@email.com',    '713-555-0308', 'Silver',   3, '2020-10-25', 2900),
  (5029, 'Sharon',   'Campbell',  's.campbell@email.com', '713-555-0309', 'Bronze',   3, '2023-02-14', 100),
  (5030, 'Kenneth',  'Diaz',      'k.diaz@email.com',     '713-555-0310', 'Silver',   3, '2021-06-20', 1600),
  (5031, 'Deborah',  'Edwards',   'd.edwards@email.com',  '512-555-0111', 'Gold',     1, '2018-11-30', 8500),
  (5032, 'Ronald',   'Flores',    'r.flores@email.com',   '512-555-0112', 'Bronze',   1, '2022-07-04', 400),
  (5033, 'Laura',    'Gonzalez',  'l.gonzalez@email.com', '210-555-0211', 'Silver',   2, '2021-03-15', 2400),
  (5034, 'Jeffrey',  'Hall',      'j.hall@email.com',     '210-555-0212', 'Gold',     2, '2019-06-22', 6500),
  (5035, 'Carolyn',  'Ingram',    'c.ingram@email.com',   '713-555-0311', 'Bronze',   3, '2022-12-01', 250),
  (5036, 'Frank',    'James',     'f.james@email.com',    '713-555-0312', 'Silver',   3, '2020-08-10', 3100),
  (5037, 'Ann',      'King',      'a.king@email.com',     '512-555-0113', 'Gold',     1, '2017-05-15', 9800),
  (5038, 'Scott',    'Lee',       's.lee@email.com',      '210-555-0213', 'Bronze',   2, '2023-04-20', 180),
  (5039, 'Diane',    'Moore',     'd.moore@email.com',    '713-555-0313', 'Silver',   3, '2021-11-08', 2000),
  (5040, 'Raymond',  'Nguyen',    'r.nguyen@email.com',   '512-555-0114', 'Gold',     1, '2019-02-28', 7400);

-- Transactions: Generate ~12,000 synthetic transactions
-- Uses a procedural approach with BigQuery scripting
DECLARE tx_id INT64 DEFAULT 1;
DECLARE batch_size INT64 DEFAULT 500;
DECLARE total_batches INT64 DEFAULT 24;
DECLARE batch_num INT64 DEFAULT 0;

-- Product IDs and their prices for lookup
CREATE TEMP TABLE product_lookup AS
SELECT product_id, unit_price FROM `wortz-project-352116.ge_grocery_demo.dim_product`;

WHILE batch_num < total_batches DO
  INSERT INTO `wortz-project-352116.ge_grocery_demo.fact_transactions`
    (transaction_id, transaction_ts, store_id, employee_id, product_id, quantity, unit_price, total_amount, payment_method, customer_id)
  SELECT
    tx_id + ROW_NUMBER() OVER (ORDER BY r1, r2) - 1 AS transaction_id,
    TIMESTAMP_ADD(
      TIMESTAMP '2024-10-01 08:00:00 UTC',
      INTERVAL CAST(FLOOR(RAND() * 90 * 24 * 3600) AS INT64) SECOND
    ) AS transaction_ts,
    store_ids.store_id,
    employee_ids.employee_id,
    p.product_id,
    CAST(CEIL(RAND() * 5) AS INT64) AS quantity,
    p.unit_price,
    ROUND(CAST(CEIL(RAND() * 5) AS INT64) * p.unit_price, 2) AS total_amount,
    CASE CAST(FLOOR(RAND() * 4) AS INT64)
      WHEN 0 THEN 'Credit Card'
      WHEN 1 THEN 'Debit Card'
      WHEN 2 THEN 'Cash'
      ELSE 'Mobile Pay'
    END AS payment_method,
    CASE WHEN RAND() > 0.3 THEN customer_ids.customer_id ELSE NULL END AS customer_id
  FROM
    UNNEST(GENERATE_ARRAY(1, batch_size)) AS r1,
    UNNEST([1]) AS r2,
    (SELECT store_id FROM `wortz-project-352116.ge_grocery_demo.dim_store` ORDER BY RAND() LIMIT 1) AS store_ids,
    (SELECT employee_id FROM `wortz-project-352116.ge_grocery_demo.dim_employee` ORDER BY RAND() LIMIT 1) AS employee_ids,
    (SELECT product_id, unit_price FROM product_lookup ORDER BY RAND() LIMIT 1) AS p,
    (SELECT customer_id FROM `wortz-project-352116.ge_grocery_demo.dim_customer` ORDER BY RAND() LIMIT 1) AS customer_ids;

  SET tx_id = tx_id + batch_size;
  SET batch_num = batch_num + 1;
END WHILE;
