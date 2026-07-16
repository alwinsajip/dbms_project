# Prior Art Awareness Notes

> **DISCLAIMER:** This document reflects the engineer's informal awareness of adjacent systems and publications encountered during development. It is NOT a formal patentability search or novelty opinion. A licensed patent attorney should conduct a professional prior-art search before making any patentability determination.

---

## Academic / Research Systems

### 1. OtterTune (CMU Database Group)
Automatic database configuration tuning using machine learning. Uses Gaussian Process regression and Lasso to recommend DBMS configuration knobs. Primarily focuses on static configuration parameters (like PostgreSQL's shared_buffers, work_mem) rather than structural schema evolution (indexing, partitioning, compression).

**Distinction from SEDBMS:** OtterTune recommends knob settings; SEDBMS proposes structural DDL modifications, validates in an isolated twin, and deploys/rolls back autonomously. OtterTune does not include a digital-twin validation stage or automated rollback.

*Reference: Van Aken et al., "Automatic Database Management System Tuning Through Large-scale Machine Learning", SIGMOD 2017.*

### 2. Database Cracking / Adaptive Indexing (CWI / Actian)
Technique where indexes are incrementally built and reorganized as queries arrive, partitioning data on-the-fly based on accessed values. Systems like MonetDB implement cracking as a physical design primitive.

**Distinction from SEDBMS:** Cracking is a physical design technique within a single DBMS kernel. SEDBMS is a control-plane that operates *above* the database, generating arbitrary DDL modifications, validating them in an isolated twin, and managing the deployment lifecycle. SEDBMS does not require kernel modifications.

*Reference: Idreos et al., "Database Cracking", CIDR 2007.*

### 3. NoDB / Adaptive Storage (Harvard DASlab)
Systems like Data Vaults and NoDB that adapt storage and indexing based on observed access patterns, operating at the raw-file level.

**Distinction from SEDBMS:** These are storage engine-level approaches. SEDBMS operates at the logical DDL/config level and includes a safety/validation layer not present in these systems.

### 4. Self-Driving Database Management Systems (Oracle, IBM, Teradata)
Commercial systems with varying degrees of autonomous capability:
- **Oracle Autonomous Database** — Automated patching, tuning, and scaling. Includes automated index tuning (SQL Access Advisor).
- **IBM Db2 Advisor** — Recommends indexes, MQTs, and partitioning.
- **Teradata SystemFE** — Workload management and automated tuning.

**Distinction from SEDBMS:** These are generally monolithic vendor implementations with integrated advisors. SEDBMS is an open-architecture, extensible control-plane with explicit digital-twin validation, staged deployment, and automatic rollback as separable claim elements. The architecture is DBMS-agnostic (the DBMS adapter is a swappable layer).

---

## Open-Source Tools

### 5. pg_stat_statements + pgBadger / pg_tail
PostgreSQL query logging and analysis tools. Provide workload visibility but no automated structural modification generation or deployment.

### 6. pganalyze / pgtune
pganalyze provides query monitoring and index recommendations. pgtune generates configuration recommendations. Neither includes digital-twin validation, automated deployment, or rollback.

### 7. pt-query-digest (Percona Toolkit)
MySQL query analysis tool. No automated modification or validation.

### 8. pgBackRest / pg_basebackup
Backup and replication tools used for creating replicas. DTO uses pg_basebackup for twin provisioning but the novel element is the orchestration lifecycle (provision→apply→replay→evaluate→destroy).

---

## Patents

A preliminary search (conducted via public patent databases, not a professional search) identified the following potentially relevant patent classifications:
- G06F 16/21 (Database design, administration, maintenance)
- G06F 16/23 (Updating)
- G06F 16/27 (Replication)
- G06F 11/30 (Monitoring)
- G06F 11/34 (Performance evaluation)

**No specific patents were reviewed in detail.** A professional prior-art search should be conducted targeting adaptive database tuning, automated schema evolution, database digital twins, automated rollback systems, and policy-governed autonomous database operations.

---

## Additional Notes

- The combination of **digital-twin validation** + **staged deployment with health-check gate** + **automatic regression-driven rollback** as a closed loop appears to be a novel combination based on informal awareness. However, individual elements may exist in various systems.
- The **policy-constrained autonomous operation** layer (block_time, block_table, max_risk) is believed to be novel as a governance layer for autonomous DBMS modification.
- The **modular strategy architecture** with documented swappable strategy interface for ML-based learning may strengthen the disclosure but individual strategy modules (indexing, etc.) are well-known techniques — the novelty lies in the autonomous closed-loop control.
