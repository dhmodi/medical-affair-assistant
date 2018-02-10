CREATE TABLE `dq_score` (
	`country` varchar
	,`trend` integer
	,`score` integer
	,`datatype` varchar
)

WITH (
	OIDS=FALSE
) ;

CREATE TABLE `known_issues`` (
	`datatype` varchar NULL,
	`country` varchar NULL,
	`Dimension` varchar NULL,
	`quality_check` varchar NULL,
	`fail_count` integer NULL
)
WITH (
	OIDS=FALSE
) ;
