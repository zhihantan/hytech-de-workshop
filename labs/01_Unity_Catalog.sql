-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 01 · Unity Catalog — 数据治理 (Data governance) · LAB
-- MAGIC 填写 `TODO`（答案在 `solutions/01_Unity_Catalog`）
-- MAGIC
-- MAGIC **目标 (Goals):** 三级命名空间 · 所有权 · 授权 · 视图 · 标签 · 列掩码 · 行过滤 · 血缘
-- MAGIC
-- MAGIC `catalog.schema.table` — 例如 `hytech_de_workshop.u_zhang_san.users_snapshot`。
-- MAGIC 本 notebook 的所有对象都建在**你自己的 schema** 里（你是 owner）。

-- COMMAND ----------

-- Your schema = u_<email name>; a SQL session variable keeps the notebook identical for everyone
DECLARE OR REPLACE VARIABLE my_schema STRING DEFAULT
  'u_' || regexp_replace(lower(split_part(current_user(), '@', 1)), '[^a-z0-9]', '_');

USE CATALOG hytech_de_workshop;
USE SCHEMA IDENTIFIER(my_schema);
SELECT current_catalog() AS catalog, current_schema() AS schema, current_user() AS me;

-- COMMAND ----------

-- MAGIC %md ## 1 · 浏览三级命名空间 (Explore the namespace)

-- COMMAND ----------

SHOW SCHEMAS IN hytech_de_workshop;

-- COMMAND ----------

SHOW VOLUMES IN hytech_de_workshop.raw;

-- COMMAND ----------

LIST '/Volumes/hytech_de_workshop/raw/landing/mt5/mt5-sg-01/';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2 · 建一张受管表 (Create a managed table)
-- MAGIC 从 4 台服务器的 DMS 全量文件读取客户账户。`_metadata.file_path` 告诉我们每行来自哪台服务器。

-- COMMAND ----------

CREATE OR REPLACE TABLE users_snapshot
COMMENT 'MT5 client accounts from the DMS full load (all servers) — lab 01'
AS SELECT
  regexp_extract(_metadata.file_path, '/mt5/([^/]+)/', 1) AS server_id,
  Login                                                   AS login,
  split_part(`Group`, '\\', 2)                            AS brand,
  FirstName                                               AS first_name,
  LastName                                                AS last_name,
  Country                                                 AS country,
  Email                                                   AS email,
  Phone                                                   AS phone,
  Status                                                  AS status,
  Leverage                                                AS leverage
FROM read_files('/Volumes/hytech_de_workshop/raw/landing/mt5/*/mt5_users/LOAD00000001.parquet', format => 'parquet');

SELECT * FROM users_snapshot LIMIT 10;

-- COMMAND ----------

-- MAGIC %md ## 3 · 所有权与授权 (Ownership and grants)

-- COMMAND ----------

-- "Owner" row: you own what you create
DESCRIBE TABLE EXTENDED users_snapshot;

-- COMMAND ----------

-- Grant to a GROUP (never to individuals). de_workshop_sz = all workshop participants.
GRANT SELECT ON TABLE users_snapshot TO `de_workshop_sz`;
SHOW GRANTS ON TABLE users_snapshot;

-- COMMAND ----------

REVOKE SELECT ON TABLE users_snapshot FROM `de_workshop_sz`;
SHOW GRANTS ON TABLE users_snapshot;

-- COMMAND ----------

-- MAGIC %md ## 4 · 视图 (Views) — share an aggregate, not the PII

-- COMMAND ----------

CREATE OR REPLACE VIEW v_clients_by_country
COMMENT 'Client counts and average leverage per brand and country (no PII)'
-- TODO 1 · number of clients and average leverage (rounded) per brand and country
AS SELECT brand, country, ____ AS clients, ____ AS avg_leverage
FROM users_snapshot
GROUP BY ALL;

SELECT * FROM v_clients_by_country ORDER BY clients DESC LIMIT 10;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 5 · 标签 (Tags) — classify sensitive columns
-- MAGIC Hytech 已有“列标签 + 下游检查”框架；Unity Catalog 原生支持列标签，并可驱动 ABAC 策略。
-- MAGIC 如果某个标签键是**治理标签 (governed tag)**，只能使用账户管理员允许的值，否则报错
-- MAGIC `UC_TAG_POLICY_VALUE_NOT_ALLOWED` —— 这就是公司级标签规范的强制力。

-- COMMAND ----------

ALTER TABLE users_snapshot ALTER COLUMN email SET TAGS ('hytech_pii' = 'email');
-- TODO 2 · tag the phone column as hytech_pii = phone (same pattern as the line above)
____;
ALTER TABLE users_snapshot SET TAGS ('hytech_sensitivity' = 'L3', 'hytech_domain' = 'client');

SELECT column_name, tag_name, tag_value
FROM information_schema.column_tags
WHERE schema_name = my_schema AND table_name = 'users_snapshot';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 6 · 列掩码 (Column mask)
-- MAGIC 只有 `hytech_pii_readers` 组的成员能看到完整邮箱；其他人（包括你）看到的是掩码后的值。

-- COMMAND ----------

CREATE OR REPLACE FUNCTION mask_email(email STRING)
RETURN CASE
  WHEN is_account_group_member('hytech_pii_readers') THEN email
  ELSE regexp_replace(email, '^(.)[^@]*', '$1***')
END;

-- TODO 3 · attach the mask function to the email column
ALTER TABLE users_snapshot ALTER COLUMN email SET MASK ____;

SELECT login, first_name, email FROM users_snapshot LIMIT 5;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 7 · 行过滤 (Row filter)
-- MAGIC 例如：Apex 品牌的分析师只能看到 Apex 的客户。

-- COMMAND ----------

CREATE OR REPLACE FUNCTION brand_filter(brand STRING)
RETURN is_account_group_member('hytech_all_brands') OR brand = 'Apex';

-- TODO 4 · attach brand_filter, passing the brand column
ALTER TABLE users_snapshot SET ROW FILTER ____ ON (____);

SELECT brand, count(*) AS clients FROM users_snapshot GROUP BY brand;

-- COMMAND ----------

-- Remove the filter again (the rest of the workshop needs all brands)
ALTER TABLE users_snapshot DROP ROW FILTER;
SELECT brand, count(*) AS clients FROM users_snapshot GROUP BY brand;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 8 · 血缘 (Lineage)
-- MAGIC 打开 **Catalog Explorer → `v_clients_by_country` → Lineage**：可以看到它来自 `users_snapshot`，而后者来自 landing volume 的文件。
-- MAGIC
-- MAGIC ## 9 · 讲师演示 (Instructor demo) — ABAC with governed tags
-- MAGIC 治理标签（governed tags）由账户管理员定义允许的值；一条 ABAC 策略就能让**所有**打了 `pii` 标签的列自动被掩码，
-- MAGIC 新建的表也会被自动保护——不需要逐表 `SET MASK`。这正是 Hytech 公司级数据安全策略需要的扩展方式。
