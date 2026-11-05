-- Google Ads conversions per campaign per conversion action per Monday-start week.
-- TEMPLATE: see google_ads_cost.sql. Output: week, campaign_id, action, conversions
SELECT
  DATE_TRUNC(segments_date, WEEK(MONDAY))     AS week,
  CAST(campaign_id AS STRING)                 AS campaign_id,
  segments_conversion_action_name             AS action,
  SUM(metrics_conversions)                    AS conversions
FROM `{dataset}.p_ads_CampaignConversionStats_*`
WHERE CAST(customer_id AS STRING) = @customer_id
  AND segments_date BETWEEN @start AND @end
GROUP BY week, campaign_id, action
