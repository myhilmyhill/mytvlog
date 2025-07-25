CREATE TABLE IF NOT EXISTS `{DATASET}.programs` (
  id STRING NOT NULL,
  event_id INT64 NOT NULL,
  service_id INT64 NOT NULL,
  name STRING NOT NULL,
  start_time TIMESTAMP NOT NULL,
  duration INT64 NOT NULL,
  text STRING,
  ext_text STRING,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY(id) NOT ENFORCED
)
PARTITION BY DATE(start_time);

CREATE TABLE IF NOT EXISTS `{DATASET}.recordings` (
  id STRING NOT NULL,
  program_id STRING NOT NULL,
  file_path STRING NOT NULL,
  file_size INT64,
  watched_at TIMESTAMP,
  deleted_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY(id) NOT ENFORCED,
  FOREIGN KEY(program_id) REFERENCES {DATASET}.programs(id) NOT ENFORCED
)
PARTITION BY DATE(created_at);

CREATE TABLE IF NOT EXISTS `{DATASET}.views` (
  program_id STRING NOT NULL,
  viewed_time TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY(program_id) REFERENCES {DATASET}.programs(id) NOT ENFORCED
)
PARTITION BY DATE(viewed_time);
