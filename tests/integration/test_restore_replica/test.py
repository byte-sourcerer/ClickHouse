import time

import pytest

from helpers.cluster import ClickHouseCluster, ClickHouseKiller
from helpers.test_tools import assert_eq_with_retry


def fill_nodes(nodes):
    for node in nodes:
        node.query("DROP TABLE IF EXISTS test SYNC")

    for node in nodes:
        node.query(
            """
            CREATE TABLE test(n UInt32)
            ENGINE = ReplicatedMergeTree('/clickhouse/tables/test/', '{replica}')
            ORDER BY n PARTITION BY n % 10;
        """.format(
                replica=node.name
            )
        )


cluster = ClickHouseCluster(__file__)
configs = ["configs/remote_servers.xml", "configs/fast_background_pool.xml"]

node_1 = cluster.add_instance("replica1", with_zookeeper=True, main_configs=configs)
node_2 = cluster.add_instance("replica2", with_zookeeper=True, main_configs=configs)
node_3 = cluster.add_instance("replica3", with_zookeeper=True, main_configs=configs)
nodes = [node_1, node_2, node_3]


def fill_table():
    fill_nodes(nodes)
    check_data(0, 0)

    # it will create multiple parts in each partition and probably cause merges
    node_1.query("INSERT INTO test SELECT number + 0 FROM numbers(200)")
    node_1.query("INSERT INTO test SELECT number + 200 FROM numbers(200)")
    node_1.query("INSERT INTO test SELECT number + 400 FROM numbers(200)")
    node_1.query("INSERT INTO test SELECT number + 600 FROM numbers(200)")
    node_1.query("INSERT INTO test SELECT number + 800 FROM numbers(200)")
    check_data(499500, 1000)


# kazoo.delete may throw NotEmptyError on concurrent modifications of the path
def zk_rmr_with_retries(zk, path):
    for i in range(1, 10):
        try:
            zk.delete(path, recursive=True)
            return
        except Exception as ex:
            print(ex)
            time.sleep(0.5)
    assert False


@pytest.fixture(scope="module")
def start_cluster():
    try:
        cluster.start()
        fill_nodes(nodes)
        yield cluster

    except Exception as ex:
        print(ex)

    finally:
        cluster.shutdown()


def check_data(_sum: int, count: int) -> None:
    res = "{}\t{}\n".format(_sum, count)
    assert_eq_with_retry(node_1, "SELECT sum(n), count() FROM test", res)
    assert_eq_with_retry(node_2, "SELECT sum(n), count() FROM test", res)
    assert_eq_with_retry(node_3, "SELECT sum(n), count() FROM test", res)


def check_after_restoration():
    check_data(1999000, 2000)

    for node in nodes:
        node.query_and_get_error("SYSTEM RESTORE REPLICA test")


def test_restore_replica_invalid_tables(start_cluster):
    print("Checking the invocation on non-existent and non-replicated tables")
    node_1.query_and_get_error("SYSTEM RESTORE REPLICA i_dont_exist_42")
    node_1.query_and_get_error("SYSTEM RESTORE REPLICA no_db.i_dont_exist_42")
    node_1.query_and_get_error("SYSTEM RESTORE REPLICA system.numbers")


def test_restore_replica_sequential(start_cluster):
    zk = cluster.get_kazoo_client("zoo1")
    fill_table()

    print("Deleting root ZK path metadata")
    zk_rmr_with_retries(zk, "/clickhouse/tables/test")
    assert zk.exists("/clickhouse/tables/test") is None

    node_1.query("SYSTEM RESTART REPLICA test")
    node_1.query_and_get_error(
        "INSERT INTO test SELECT number AS num FROM numbers(1000,2000) WHERE num % 2 = 0"
    )

    print("Restoring replica1")

    node_1.query("SYSTEM RESTORE REPLICA test")
    assert zk.exists("/clickhouse/tables/test")
    check_data(499500, 1000)

    node_1.query("INSERT INTO test SELECT number + 1000 FROM numbers(1000)")

    print("Restoring other replicas")

    node_2.query("SYSTEM RESTART REPLICA test")
    node_2.query("SYSTEM RESTORE REPLICA test")

    node_3.query("SYSTEM RESTART REPLICA test")
    node_3.query("SYSTEM RESTORE REPLICA test")

    node_2.query("SYSTEM SYNC REPLICA test")
    node_3.query("SYSTEM SYNC REPLICA test")

    check_after_restoration()


def test_restore_replica_parallel(start_cluster):
    zk = cluster.get_kazoo_client("zoo1")
    fill_table()

    print("Deleting root ZK path metadata")
    zk_rmr_with_retries(zk, "/clickhouse/tables/test")
    assert zk.exists("/clickhouse/tables/test") is None

    node_1.query("SYSTEM RESTART REPLICA test")
    node_1.query_and_get_error(
        "INSERT INTO test SELECT number AS num FROM numbers(1000,2000) WHERE num % 2 = 0"
    )

    print("Restoring replicas in parallel")

    node_2.query("SYSTEM RESTART REPLICA test")
    node_3.query("SYSTEM RESTART REPLICA test")

    node_1.query("SYSTEM RESTORE REPLICA test ON CLUSTER test_cluster")

    assert zk.exists("/clickhouse/tables/test")
    check_data(499500, 1000)

    node_1.query("INSERT INTO test SELECT number + 1000 FROM numbers(1000)")

    check_after_restoration()


def test_restore_replica_alive_replicas(start_cluster):
    zk = cluster.get_kazoo_client("zoo1")
    fill_table()

    print("Deleting replica2 path, trying to restore replica1")
    zk_rmr_with_retries(zk, "/clickhouse/tables/test/replicas/replica2")
    assert zk.exists("/clickhouse/tables/test/replicas/replica2") is None
    node_1.query_and_get_error("SYSTEM RESTORE REPLICA test")

    print("Deleting replica1 path, trying to restore replica1")
    zk_rmr_with_retries(zk, "/clickhouse/tables/test/replicas/replica1")
    assert zk.exists("/clickhouse/tables/test/replicas/replica1") is None

    node_1.query("SYSTEM RESTART REPLICA test")
    node_1.query("SYSTEM RESTORE REPLICA test")

    node_2.query("SYSTEM RESTART REPLICA test")
    node_2.query("SYSTEM RESTORE REPLICA test")

    check_data(499500, 1000)

    node_1.query("INSERT INTO test SELECT number + 1000 FROM numbers(1000)")

    node_2.query("SYSTEM SYNC REPLICA test")
    node_3.query("SYSTEM SYNC REPLICA test")

    check_after_restoration()


def test_fix_metadata_version_on_attach_part_after_restore(start_cluster):
    zk = cluster.get_kazoo_client("zoo1")

    node_1.query("DROP TABLE IF EXISTS test_ttl ON CLUSTER 'test_cluster' SYNC")
    for node in [node_1, node_2]:
        node.query(
            """
            CREATE TABLE test_ttl(n UInt32, d DateTime)
            ENGINE = ReplicatedMergeTree('/clickhouse/tables/test_ttl/', '{replica}')
            TTL d + INTERVAL 5 SECOND DELETE
            ORDER BY n PARTITION BY n % 10
            SETTINGS merge_with_ttl_timeout = 0, number_of_free_entries_in_pool_to_execute_mutation = 0;
        """.format(
                replica=node.name
            )
        )

    # Alter metadata to increment metadata version of the table
    node_1.query("ALTER TABLE test_ttl ADD COLUMN Added1 UInt32")
    node_1.query("ALTER TABLE test_ttl DROP COLUMN Added1")

    node_1.query("SYSTEM STOP TTL MERGES test_ttl")

    # Create a part
    node_1.query("INSERT INTO test_ttl VALUES (1, now())")

    # Delete root zk metadata path for the table
    zk_rmr_with_retries(zk, "/clickhouse/tables/test_ttl")

    # Restore replicas
    node_1.query("SYSTEM RESTART REPLICA test_ttl")
    node_1.query("SYSTEM RESTORE REPLICA test_ttl")
    # Disable TTL merges on node_1. We expect it to be done on node_2
    node_1.query("SYSTEM STOP TTL MERGES test_ttl")

    node_2.query("SYSTEM RESTART REPLICA test_ttl")
    node_2.query("SYSTEM RESTORE REPLICA test_ttl")

    # TTL merge should work.
    # Before fix it is failed due to metadata version discrepancy and we will have in the log:
    # "Source part metadata version 2 is newer then the table metadata version 0. ALTER_METADATA is still in progress"
    assert_eq_with_retry(
        node_2, "SELECT count() FROM test_ttl", "0\n", retry_count=60, sleep_time=1
    )
