WHERE
	Age BETWEEN 30 AND 40
WITH RECURSIVE employee_hierarchy AS (
    SELECT employee_id, manager_id, first_name, last_name, 1 AS level
    FROM employees
    WHERE manager_id IS NULL
    UNION ALL
    SELECT e.employee_id, e.manager_id, e.first_name, e.last_name, eh.level + 1
    FROM employees e
    JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
),
sales_summary AS (
    SELECT 
        p.product_id,
        p.product_name,
        c.category_name,
        SUM(od.quantity * od.unit_price * (1 - od.discount)) AS total_sales,
        COUNT(DISTINCT o.customer_id) AS unique_customers,
        AVG(od.quantity) AS avg_quantity_per_order,
        RANK() OVER (PARTITION BY c.category_id ORDER BY SUM(od.quantity * od.unit_price * (1 - od.discount)) DESC) AS sales_rank
    FROM products p
    JOIN order_details od ON p.product_id = od.product_id
    JOIN orders o ON od.order_id = o.order_id
    JOIN categories c ON p.category_id = c.category_id
    WHERE o.order_date BETWEEN '2022-01-01' AND '2022-12-31'
    GROUP BY p.product_id, p.product_name, c.category_name, c.category_id
    
),
customer_segmentation AS (
    SELECT 
        c.customer_id,
        c.company_name,
        SUM(o.total_amount) AS total_spent,
        COUNT(o.order_id) AS order_count,
        MAX(o.order_date) AS last_order_date,
        DATEDIFF(DAY, MAX(o.order_date), GETDATE()) AS days_since_last_order,
        NTILE(4) OVER (ORDER BY SUM(o.total_amount) DESC) AS customer_segment
            undergoes
            JOIN (
                SELECT
                    stay.StayID,
                    stay.Patient,
                    stay.Room AS room,
                    a.totalStays
                FROM
                    stay
                    INNER JOIN (
                        SELECT
                            patient,
                            COUNT(*) AS totalStays
                        FROM
                            stay
                        GROUP BY
                            patient
                        HAVING
                            totalStays > 1) AS a ON stay.Patient = a.patient) AS b ON undergoes.Patient = b.Patient
                    AND undergoes.Stay = b.StayID) AS c ON treatment.Code = c.Treatment) AS d
        GROUP BY
            patient) AS e ON patient.SSN = e.patient
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.company_name
)

SELECT 
    eh.employee_id,
    eh.first_name + ' ' + eh.last_name AS employee_name,
    eh.level AS hierarchy_level,
    ss.product_name,
    ss.category_name,
    ss.total_sales,
    ss.unique_customers,
    ss.avg_quantity_per_order,
    ss.sales_rank,
    cs.company_name AS top_customer,
    cs.total_spent AS top_customer_spent,
    cs.customer_segment,
    (SELECT AVG(sub_ss.total_sales) 
     FROM sales_summary sub_ss 
     WHERE sub_ss.category_name = ss.category_name) AS avg_category_sales,
    CASE 
        WHEN ss.sales_rank = 1 THEN 'Top Performer'
        WHEN ss.sales_rank <= 3 THEN 'High Performer'
        WHEN ss.sales_rank <= 10 THEN 'Average Performer'
        ELSE 'Low Performer'
    END AS performance_category,
    LAG(ss.total_sales) OVER (PARTITION BY ss.category_name ORDER BY ss.total_sales DESC) AS prev_product_sales,
    LEAD(ss.total_sales) OVER (PARTITION BY ss.category_name ORDER BY ss.total_sales DESC) AS next_product_sales
FROM employee_hierarchy eh
CROSS APPLY (
    SELECT TOP 1 *
    FROM sales_summary ss
    ORDER BY ss.total_sales DESC
) ss
OUTER APPLY (
    SELECT TOP 1 *
    FROM customer_segmentation cs
    WHERE cs.customer_segment = 1
    ORDER BY cs.total_spent DESC
) cs
WHERE eh.level <= 3
  AND ss.total_sales > (SELECT AVG(total_sales) * 1.5 FROM sales_summary)
  AND EXISTS (
      SELECT 1
      FROM orders o
      JOIN order_details od ON o.order_id = od.order_id
      WHERE o.employee_id = eh.employee_id
        AND od.product_id = ss.product_id
  )
ORDER BY eh.level, ss.total_sales DESC, cs.total_spent DESC
OPTION (MAXRECURSION 0, RECOMPILE, USE HINT('ENABLE_PARALLEL_PLAN_PREFERENCE'));
