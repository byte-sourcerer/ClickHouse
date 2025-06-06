---
description: 'Provides a table-like interface to `SELECT` and `INSERT` data from Google
  Cloud Storage. Requires the `Storage Object User` IAM role.'
keywords: ['gcs', 'bucket']
sidebar_label: 'gcs'
sidebar_position: 70
slug: /sql-reference/table-functions/gcs
title: 'gcs'
---

# gcs Table Function

Provides a table-like interface to `SELECT` and `INSERT` data from [Google Cloud Storage](https://cloud.google.com/storage/). Requires the [`Storage Object User` IAM role](https://cloud.google.com/storage/docs/access-control/iam-roles).

This is an alias of the [s3 table function](../../sql-reference/table-functions/s3.md).

If you have multiple replicas in your cluster, you can use the [s3Cluster function](../../sql-reference/table-functions/s3Cluster.md) (which works with GCS) instead to parallelize inserts.

## Syntax {#syntax}

```sql
gcs(url [, NOSIGN | hmac_key, hmac_secret] [,format] [,structure] [,compression_method])
gcs(named_collection[, option=value [,..]])
```

:::tip GCS
The GCS Table Function integrates with Google Cloud Storage by using the GCS XML API and HMAC keys. 
See the [Google interoperability docs]( https://cloud.google.com/storage/docs/interoperability) for more details about the endpoint and HMAC.
:::

## Arguments {#arguments}

| Argument                     | Description                                                                                                                                                                              |
|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `url`                        | Bucket path to file. Supports following wildcards in readonly mode: `*`, `**`, `?`, `{abc,def}` and `{N..M}` where `N`, `M` — numbers, `'abc'`, `'def'` — strings.                       |
| `NOSIGN`                     | If this keyword is provided in place of credentials, all the requests will not be signed.                                                                                                |
| `hmac_key` and `hmac_secret` | Keys that specify credentials to use with given endpoint. Optional.                                                                                                                      |
| `format`                     | The [format](/sql-reference/formats) of the file.                                                                                                                                        |
| `structure`                  | Structure of the table. Format `'column1_name column1_type, column2_name column2_type, ...'`.                                                                                            |
| `compression_method`         | Parameter is optional. Supported values: `none`, `gzip` or `gz`, `brotli` or `br`, `xz` or `LZMA`, `zstd` or `zst`. By default, it will autodetect compression method by file extension. |

:::note GCS
The GCS path is in this format as the endpoint for the Google XML API is different than the JSON API:

```text
  https://storage.googleapis.com/<bucket>/<folder>/<filename(s)>
```

and not ~~https://storage.cloud.google.com~~.
:::

Arguments can also be passed using [named collections](operations/named-collections.md). In this case `url`, `format`, `structure`, `compression_method` work in the same way, and some extra parameters are supported:

| Parameter                     | Description                                                                                                                                                                                                                       |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `access_key_id`               | `hmac_key`, optional.                                                                                                                                                                                                             |
| `secret_access_key`           | `hmac_secret`, optional.                                                                                                                                                                                                          |
| `filename`                    | Appended to the url if specified.                                                                                                                                                                                                 |
| `use_environment_credentials` | Enabled by default, allows passing extra parameters using environment variables `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`, `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN`, `AWS_EC2_METADATA_DISABLED`. |
| `no_sign_request`             | Disabled by default.                                                                                                                                                                                                              |
| `expiration_window_seconds`   | Default value is 120.                                                                                                                                                                                                             |

## Returned value {#returned_value}

A table with the specified structure for reading or writing data in the specified file.

## Examples {#examples}

Selecting the first two rows from the table from GCS file `https://storage.googleapis.com/my-test-bucket-768/data.csv`:

```sql
SELECT *
FROM gcs('https://storage.googleapis.com/clickhouse_public_datasets/my-test-bucket-768/data.csv.gz', 'CSV', 'column1 UInt32, column2 UInt32, column3 UInt32')
LIMIT 2;
```

```text
┌─column1─┬─column2─┬─column3─┐
│       1 │       2 │       3 │
│       3 │       2 │       1 │
└─────────┴─────────┴─────────┘
```

The similar but from file with `gzip` compression method:

```sql
SELECT *
FROM gcs('https://storage.googleapis.com/clickhouse_public_datasets/my-test-bucket-768/data.csv.gz', 'CSV', 'column1 UInt32, column2 UInt32, column3 UInt32', 'gzip')
LIMIT 2;
```

```text
┌─column1─┬─column2─┬─column3─┐
│       1 │       2 │       3 │
│       3 │       2 │       1 │
└─────────┴─────────┴─────────┘
```

## Usage {#usage}

Suppose that we have several files with following URIs on GCS:

-   'https://storage.googleapis.com/my-test-bucket-768/some_prefix/some_file_1.csv'
-   'https://storage.googleapis.com/my-test-bucket-768/some_prefix/some_file_2.csv'
-   'https://storage.googleapis.com/my-test-bucket-768/some_prefix/some_file_3.csv'
-   'https://storage.googleapis.com/my-test-bucket-768/some_prefix/some_file_4.csv'
-   'https://storage.googleapis.com/my-test-bucket-768/another_prefix/some_file_1.csv'
-   'https://storage.googleapis.com/my-test-bucket-768/another_prefix/some_file_2.csv'
-   'https://storage.googleapis.com/my-test-bucket-768/another_prefix/some_file_3.csv'
-   'https://storage.googleapis.com/my-test-bucket-768/another_prefix/some_file_4.csv'

Count the amount of rows in files ending with numbers from 1 to 3:

```sql
SELECT count(*)
FROM gcs('https://storage.googleapis.com/clickhouse_public_datasets/my-test-bucket-768/{some,another}_prefix/some_file_{1..3}.csv', 'CSV', 'column1 UInt32, column2 UInt32, column3 UInt32')
```

```text
┌─count()─┐
│      18 │
└─────────┘
```

Count the total amount of rows in all files in these two directories:

```sql
SELECT count(*)
FROM gcs('https://storage.googleapis.com/clickhouse_public_datasets/my-test-bucket-768/{some,another}_prefix/*', 'CSV', 'column1 UInt32, column2 UInt32, column3 UInt32')
```

```text
┌─count()─┐
│      24 │
└─────────┘
```

:::warning
If your listing of files contains number ranges with leading zeros, use the construction with braces for each digit separately or use `?`.
:::

Count the total amount of rows in files named `file-000.csv`, `file-001.csv`, ... , `file-999.csv`:

```sql
SELECT count(*)
FROM gcs('https://storage.googleapis.com/clickhouse_public_datasets/my-test-bucket-768/big_prefix/file-{000..999}.csv', 'CSV', 'name String, value UInt32');
```

```text
┌─count()─┐
│      12 │
└─────────┘
```

Insert data into file `test-data.csv.gz`:

```sql
INSERT INTO FUNCTION gcs('https://storage.googleapis.com/my-test-bucket-768/test-data.csv.gz', 'CSV', 'name String, value UInt32', 'gzip')
VALUES ('test-data', 1), ('test-data-2', 2);
```

Insert data into file `test-data.csv.gz` from existing table:

```sql
INSERT INTO FUNCTION gcs('https://storage.googleapis.com/my-test-bucket-768/test-data.csv.gz', 'CSV', 'name String, value UInt32', 'gzip')
SELECT name, value FROM existing_table;
```

Glob ** can be used for recursive directory traversal. Consider the below example, it will fetch all files from `my-test-bucket-768` directory recursively:

```sql
SELECT * FROM gcs('https://storage.googleapis.com/my-test-bucket-768/**', 'CSV', 'name String, value UInt32', 'gzip');
```

The below get data from all `test-data.csv.gz` files from any folder inside `my-test-bucket` directory recursively:

```sql
SELECT * FROM gcs('https://storage.googleapis.com/my-test-bucket-768/**/test-data.csv.gz', 'CSV', 'name String, value UInt32', 'gzip');
```

For production use cases it is recommended to use [named collections](operations/named-collections.md). Here is the example:
```sql

CREATE NAMED COLLECTION creds AS
        access_key_id = '***',
        secret_access_key = '***';
SELECT count(*)
FROM gcs(creds, url='https://s3-object-url.csv')
```

## Partitioned Write {#partitioned-write}

If you specify `PARTITION BY` expression when inserting data into `GCS` table, a separate file is created for each partition value. Splitting the data into separate files helps to improve reading operations efficiency.

**Examples**

1. Using partition ID in a key creates separate files:

```sql
INSERT INTO TABLE FUNCTION
    gcs('http://bucket.amazonaws.com/my_bucket/file_{_partition_id}.csv', 'CSV', 'a String, b UInt32, c UInt32')
    PARTITION BY a VALUES ('x', 2, 3), ('x', 4, 5), ('y', 11, 12), ('y', 13, 14), ('z', 21, 22), ('z', 23, 24);
```
As a result, the data is written into three files: `file_x.csv`, `file_y.csv`, and `file_z.csv`.

2. Using partition ID in a bucket name creates files in different buckets:

```sql
INSERT INTO TABLE FUNCTION
    gcs('http://bucket.amazonaws.com/my_bucket_{_partition_id}/file.csv', 'CSV', 'a UInt32, b UInt32, c UInt32')
    PARTITION BY a VALUES (1, 2, 3), (1, 4, 5), (10, 11, 12), (10, 13, 14), (20, 21, 22), (20, 23, 24);
```
As a result, the data is written into three files in different buckets: `my_bucket_1/file.csv`, `my_bucket_10/file.csv`, and `my_bucket_20/file.csv`.

## Related {#related}
- [S3 table function](s3.md)
- [S3 engine](../../engines/table-engines/integrations/s3.md)
