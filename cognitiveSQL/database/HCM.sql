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
	`dimension` varchar NULL,
	`quality_check` varchar NULL,
	`failcount` integer NULL
)
WITH (
	OIDS=FALSE
) ;

CREATE TABLE `graph_data` (
	`country` varchar(20) NULL,
	`product` varchar(30) NULL,
	`inquiry_month` varchar(26) NULL,
	`inquiry_count` int4 NULL
	`inquiry_year` float NULL
)
WITH (
	OIDS=FALSE
) ;
