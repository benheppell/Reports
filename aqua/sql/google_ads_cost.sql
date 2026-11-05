-- Google Ads spend per campaign per Monday-start week, for one customer.
-- TEMPLATE: written for the standard Google Ads Data Transfer schema. Aqua's own BigQuery tables
-- need checking before GOOGLE_ADS_SOURCE=bigquery is switched on; keep the output columns.
-- Output: week (DATE, Monday), campaign_id (STRING), campaign (STRING), cost (account currency),
--         impr, clicks
SELECT
  DATE_TRUNC(s.segments_date, WEEK(MONDAY)) AS week,
  CAST(s.campaign_id AS STRING)               AS campaign_id,
  ANY_VALUE(c.campaign_name)                  AS campaign,
  SUM(s.metrics_cost_micros) / 1e6            AS cost,
  SUM(s.metrics_impressions)                  AS impr,
  SUM(s.metrics_clicks)                       AS clicks
FROM `{dataset}.p_ads_CampaignBasicStats_*` s
LEFT JOIN `{dataset}.p_ads_Campaign_*` c USING (campaign_id, customer_id)
WHERE CAST(s.customer_id AS STRING) = @customer_id
  AND s.segments_date BETWEEN @start AND @end
GROUP BY week, campaign_id
HAVING impr > 0
