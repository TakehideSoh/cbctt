# Curriculum-Based Course Timetabling (CB-CTT)

Curriculum-Based Course Timetabling 問題のリポジトリです。

## 問題概要

CB-CTT問題は、大学などの教育機関における時間割作成問題です。各講義を時間枠（タイムスロット）と教室に割り当て、様々な制約を満たす解を求めます。

## 制約条件

### ハード制約（Hard Constraints）

必ず満たさなければならない制約です。これらに違反する解は実行不可能（infeasible）とみなされます。

| 制約 | 説明 |
|------|------|
| **H1: 講義の割当** | すべての講義は、指定された週あたりの回数分、時間枠と教室に割り当てられなければならない |
| **H2: 教室の占有** | 同一時間枠において、1つの教室には最大1つの講義しか割り当てられない |
| **H3: 教員の衝突回避** | 同一時間枠において、1人の教員は最大1つの講義しか担当できない |
| **H4: カリキュラムの衝突回避** | 同一カリキュラムに属する講義は、同一時間枠に割り当てられない |
| **H5: 利用不可時間枠** | 講義は、その科目で利用不可と指定された時間枠には割り当てられない |

### ソフト制約（Soft Constraints）

違反してもよいが、違反するとペナルティが課される制約です。目的関数はこれらの違反の重み付き総和を最小化します。

| 制約 | 説明 | ペナルティ |
|------|------|-----------|
| **S1: 教室容量（Room Capacity）** | 講義の受講者数が教室の座席数を超える場合、超過人数分のペナルティ | 超過学生1人あたり1点 |
| **S2: 最小稼働日数（Minimum Working Days）** | 各科目は指定された最小日数以上にわたって分散されるべき | 不足日数1日あたり5点 |
| **S3: カリキュラムの連続性（Curriculum Compactness）** | 同一カリキュラム内で、ある時間枠に講義があり、その前後の時間枠に同カリキュラムの講義がない場合（孤立講義）はペナルティ | 孤立講義1つあたり2点 |
| **S4: 教室安定性（Room Stability）** | 同一科目の講義は可能な限り同じ教室で行うべき | 使用教室数が1を超えた分だけ1点 |

## 目的関数

目的関数は、ソフト制約違反の重み付きペナルティの総和を最小化することです：

```
最小化: 1×(教室容量違反) + 5×(最小稼働日数違反) + 2×(連続性違反) + 1×(教室安定性違反)
```

## 入力ファイルフォーマット

入力ファイルは、ヘッダー部と4つのデータセクションから構成されます。

### ヘッダー部

問題の基本パラメータを定義します。

```
Name: Toy
Courses: 4
Rooms: 2
Days: 5
Periods_per_day: 4
Curricula: 2
Constraints: 8
```

| フィールド | 説明 |
|-----------|------|
| Name | インスタンス名 |
| Courses | 科目数 |
| Rooms | 教室数 |
| Days | 週あたりの日数 |
| Periods_per_day | 1日あたりの時限数 |
| Curricula | カリキュラム数 |
| Constraints | 利用不可制約の数 |

### COURSES セクション

```
COURSES:
<CourseID> <Teacher> <NumLectures> <MinWorkingDays> <NumStudents>
```

| フィールド | 説明 |
|-----------|------|
| CourseID | 科目ID（空白なしの文字列） |
| Teacher | 担当教員ID |
| NumLectures | 週あたりの講義回数 |
| MinWorkingDays | 最小稼働日数 |
| NumStudents | 受講者数 |

例: `SceCosC Ocra 3 3 30` — 科目SceCosC、教員Ocra、週3回、最小3日、30名

### ROOMS セクション

```
ROOMS:
<RoomID> <Capacity>
```

| フィールド | 説明 |
|-----------|------|
| RoomID | 教室ID |
| Capacity | 座席数 |

例: `A 32` — 教室A、32席

### CURRICULA セクション

```
CURRICULA:
<CurriculumID> <NumCourses> <CourseID1> <CourseID2> ...
```

| フィールド | 説明 |
|-----------|------|
| CurriculumID | カリキュラムID |
| NumCourses | 所属科目数 |
| CourseID... | 所属する科目IDのリスト |

例: `Cur1 3 SceCosC ArcTec TecCos` — カリキュラムCur1に3科目が所属

### UNAVAILABILITY_CONSTRAINTS セクション

```
UNAVAILABILITY_CONSTRAINTS:
<CourseID> <Day> <Period>
```

| フィールド | 説明 |
|-----------|------|
| CourseID | 科目ID |
| Day | 日（0始まり） |
| Period | 時限（0始まり） |

例: `TecCos 3 2` — 科目TecCosは3日目の2時限目に割り当て不可

ファイルは `END.` で終了します。

### 入力例

```
Name: ToyExample
Courses: 4
Rooms: 2
Days: 5
Periods_per_day: 4
Curricula: 2
Constraints: 8

COURSES:
SceCosC Ocra 3 3 30
ArcTec Indaco 3 2 42
TecCos Rosa 5 4 40
Geotec Scarlatti 5 4 18

ROOMS:
A 32
B 50

CURRICULA:
Cur1 3 SceCosC ArcTec TecCos
Cur2 2 TecCos Geotec

UNAVAILABILITY_CONSTRAINTS:
TecCos 2 0
TecCos 2 1
TecCos 3 2
TecCos 3 3
ArcTec 4 0
ArcTec 4 1
ArcTec 4 2
ArcTec 4 3

END.
```

この例では：
- 4つの科目（SceCosC, ArcTec, TecCos, Geotec）
- 2つの教室（A: 32席、B: 50席）
- 5日間、1日4時限（計20タイムスロット）
- 2つのカリキュラム（Cur1: 3科目、Cur2: 2科目）
- 8つの利用不可制約（TecCosは2日目の0-1時限と3日目の2-3時限が不可、ArcTecは4日目の全時限が不可）

## 出力ファイルフォーマット

出力ファイルは、各行が1つの講義の割り当てを表します。

```
<CourseID> <RoomID> <Day> <Period>
```

| フィールド | 説明 |
|-----------|------|
| CourseID | 科目ID |
| RoomID | 割り当てられた教室ID |
| Day | 日（0始まり、0=月曜日） |
| Period | 時限（0始まり） |

### 出力例

```
SceCosC B 3 0
SceCosC A 3 1
SceCosC A 4 0
ArcTec B 0 1
ArcTec B 1 1
ArcTec B 1 2
TecCos B 0 0
TecCos A 0 1
TecCos B 2 2
TecCos B 4 2
TecCos B 4 3
Geotec A 2 2
Geotec A 2 3
Geotec B 3 0
Geotec A 3 1
Geotec A 4 2
```

最初の行は「科目SceCosCの講義が、木曜日（3）の1時限目（0）に教室Bで行われる」ことを意味します。

行の順序は任意です。各科目は、入力で指定された講義回数分の行が必要です。

### 出力例の視覚化

上記の出力例を時間割表形式で表示すると以下のようになります。

**教室 A（32席）**

|        | 月(0) | 火(1) | 水(2)  | 木(3)   | 金(4)   |
|--------|-------|-------|--------|---------|---------|
| 1限(0) | -     | -     | -      | -       | SceCosC |
| 2限(1) | TecCos| -     | -      | SceCosC, Geotec | -  |
| 3限(2) | -     | -     | Geotec | -       | Geotec  |
| 4限(3) | -     | -     | Geotec | -       | -       |

**教室 B（50席）**

|        | 月(0) | 火(1) | 水(2)  | 木(3)   | 金(4)  |
|--------|-------|-------|--------|---------|--------|
| 1限(0) | TecCos| -     | -      | SceCosC, Geotec | - |
| 2限(1) | ArcTec| ArcTec| -      | -       | -      |
| 3限(2) | -     | ArcTec| TecCos | -       | TecCos |
| 4限(3) | -     | -     | -      | -       | TecCos |

**カリキュラム別の視点（Cur1: SceCosC, ArcTec, TecCos）**

|        | 月(0)          | 火(1)  | 水(2)  | 木(3)   | 金(4)   |
|--------|----------------|--------|--------|---------|---------|
| 1限(0) | TecCos         | -      | -      | SceCosC | SceCosC |
| 2限(1) | ArcTec, TecCos | ArcTec | -      | SceCosC | -       |
| 3限(2) | -              | ArcTec | TecCos | -       | TecCos  |
| 4限(3) | -              | -      | -      | -       | TecCos  |

**カリキュラム別の視点（Cur2: TecCos, Geotec）**

|        | 月(0)  | 火(1) | 水(2)          | 木(3)  | 金(4)          |
|--------|--------|-------|----------------|--------|----------------|
| 1限(0) | TecCos | -     | -              | Geotec | -              |
| 2限(1) | TecCos | -     | -              | Geotec | -              |
| 3限(2) | -      | -     | TecCos, Geotec | -      | TecCos, Geotec |
| 4限(3) | -      | -     | Geotec         | -      | TecCos         |

この例では複数のハード制約違反があります：
- **H4違反（カリキュラム衝突）**: Cur1の月曜2限にArcTecとTecCos、Cur2の水曜3限と金曜3限にTecCosとGeotec
- **H2違反（教室占有）**: 木曜1限に教室Bで2講義、木曜2限に教室Aで2講義

### Validator による検証結果

`validator` を使用してこの出力例を検証した結果：

```
$ ./validator examples/toy.ctt examples/toy_solution.out

[H] Courses ArcTec and TecCos have both a lecture at period 1 (day 0, timeslot 1)
[H] Courses TecCos and Geotec have both a lecture at period 10 (day 2, timeslot 2)
[H] Courses TecCos and Geotec have both a lecture at period 18 (day 4, timeslot 2)
[H] 2 lectures in room B the period 12 (day 3, timeslot 0)
[H] 2 lectures in room A the period 13 (day 3, timeslot 1)
[S(8)] Room A too small for course TecCos the period 1 (day 0, timeslot 1)
[S(5)] The course SceCosC has only 2 days of lecture
[S(5)] The course TecCos has only 3 days of lecture
[S(5)] The course Geotec has only 3 days of lecture
[S(2)] Curriculum Cur1 has an isolated lecture at period 10 (day 2, timeslot 2)
[S(2)] Curriculum Cur1 has an isolated lecture at period 16 (day 4, timeslot 0)
[S(1)] Course SceCosC uses 2 different rooms
[S(1)] Course TecCos uses 2 different rooms
[S(1)] Course Geotec uses 2 different rooms

Violations of Lectures (hard) : 0
Violations of Conflicts (hard) : 3
Violations of Availability (hard) : 0
Violations of RoomOccupation (hard) : 2
Cost of RoomCapacity (soft) : 8
Cost of MinWorkingDays (soft) : 15
Cost of CurriculumCompactness (soft) : 4
Cost of RoomStability (soft) : 3

Summary: Violations = 5, Total Cost = 30
```

**ハード制約違反（Violations = 5）**
- カリキュラム衝突: 3件（ArcTec/TecCos月曜2限、TecCos/Geotec水曜3限、TecCos/Geotec金曜3限）
- 教室占有: 2件（木曜1限教室B、木曜2限教室A）

**ソフト制約コスト（Total Cost = 30）**
- 教室容量: 8点（TecCos 40名が教室A 32席に配置、8名超過）
- 最小稼働日数: 15点（SceCosC 2/3日、TecCos 3/4日、Geotec 3/4日）
- カリキュラム連続性: 4点（2つの孤立講義）
- 教室安定性: 3点（SceCosC、TecCos、Geotec が各2教室使用）

## ソルバー

### 必要条件

```bash
pip install ortools
```

### 使い方

```bash
python solver.py <入力ファイル> [出力ファイル]
```

### 実行例

```bash
$ python solver.py examples/toy.ctt examples/toy_solved.out

Parsing instance: examples/toy.ctt
Instance: ToyExample
  Courses: 4
  Rooms: 2
  Days: 5
  Periods per day: 4
  Curricula: 2
  Unavailability constraints: 8

Solving...
Solution found! Status: OPTIMAL
Objective value (soft cost): 0.0

Solution:
SceCosC B 2 0
SceCosC B 3 0
SceCosC B 1 1
ArcTec B 3 2
ArcTec B 2 1
ArcTec B 0 0
TecCos B 0 1
TecCos B 1 2
TecCos B 2 2
TecCos B 3 1
TecCos B 1 3
Geotec A 2 1
Geotec A 0 0
Geotec A 2 3
Geotec A 1 1
Geotec A 3 0
```

### 検証・可視化（Python）

```bash
$ python validator.py examples/toy.ctt examples/toy_solved.out

Violations of Lectures (hard) : 0
Violations of Conflicts (hard) : 0
Violations of Availability (hard) : 0
Violations of RoomOccupation (hard) : 0
Cost of RoomCapacity (soft) : 0
Cost of MinWorkingDays (soft) : 0
Cost of CurriculumCompactness (soft) : 0
Cost of RoomStability (soft) : 0

Summary: Total Cost = 0

============================================================
TIMETABLE VISUALIZATION
============================================================

【Room A】(Capacity: 32)
-----------------------------------------------------
          Mon(0)   Tue(1)   Wed(2)   Thu(3)   Fri(4)
P0(0)    Geotec     -        -      Geotec     -
P1(1)      -      Geotec   Geotec     -        -
P2(2)      -        -        -        -        -
P3(3)      -        -      Geotec     -        -

【Room B】(Capacity: 50)
-----------------------------------------------------
          Mon(0)   Tue(1)   Wed(2)   Thu(3)   Fri(4)
P0(0)    ArcTec     -     SceCosC  SceCosC     -
P1(1)    TecCos  SceCosC   ArcTec   TecCos     -
P2(2)      -      TecCos   TecCos   ArcTec     -
P3(3)      -      TecCos     -        -        -
...
```

`--no-visual` オプションで可視化を省略できます。

### 検証（C++公式validator）

```bash
$ g++ -o validator validator.cc
$ ./validator examples/toy.ctt examples/toy_solved.out
```

### 実装

ソルバーは Google OR-Tools CP-SAT を使用しています。

- **決定変数**: `x[c,l,r,p]` = 科目cの講義lが教室rの時限pに割り当てられるか（0/1）
- **ハード制約**: H1〜H5をすべてモデル化
- **ソフト制約**: S1〜S4をペナルティ付きで最小化

## ベンチマークインスタンス

`benchmark/` ディレクトリに61個のベンチマークインスタンス（.ectt形式）があります。

### ITC-2007 (comp01-21)

ITC2007 Track 3 の公式ベンチマークインスタンス（21問）。

| Instance | Name | Courses | Rooms | Days | Periods | Curricula | Unavail | RoomConstr |
|----------|------|---------|-------|------|---------|-----------|---------|------------|
| comp01 | Fis0506-1 | 30 | 6 | 5 | 6 | 14 | 53 | 23 |
| comp02 | Ing0203-2 | 82 | 16 | 5 | 5 | 70 | 513 | 167 |
| comp03 | Ing0304-1 | 72 | 16 | 5 | 5 | 68 | 382 | 149 |
| comp04 | Ing0405-3 | 79 | 18 | 5 | 5 | 57 | 396 | 177 |
| comp05 | Let0405-1 | 54 | 9 | 6 | 6 | 139 | 771 | 73 |
| comp06 | Ing0506-1 | 108 | 18 | 5 | 5 | 70 | 632 | 234 |
| comp07 | Ing0607-2 | 131 | 20 | 5 | 5 | 77 | 667 | 308 |
| comp08 | Ing0607-3 | 86 | 18 | 5 | 5 | 61 | 478 | 197 |
| comp09 | Ing0304-3 | 76 | 18 | 5 | 5 | 75 | 405 | 170 |
| comp10 | Ing0405-2 | 115 | 18 | 5 | 5 | 67 | 694 | 257 |
| comp11 | Fis0506-2 | 30 | 5 | 5 | 9 | 13 | 94 | 17 |
| comp12 | Let0506-2 | 88 | 11 | 6 | 6 | 150 | 1368 | 72 |
| comp13 | Ing0506-3 | 82 | 19 | 5 | 5 | 66 | 468 | 116 |
| comp14 | Ing0708-1 | 85 | 17 | 5 | 5 | 60 | 486 | 105 |
| comp15 | Ing0203-1 | 72 | 16 | 5 | 5 | 68 | 382 | 85 |
| comp16 | Ing0607-1 | 108 | 20 | 5 | 5 | 71 | 518 | 175 |
| comp17 | Ing0405-1 | 99 | 17 | 5 | 5 | 70 | 548 | 129 |
| comp18 | Let0304-1 | 47 | 9 | 6 | 6 | 52 | 594 | 30 |
| comp19 | Ing0203-3 | 74 | 16 | 5 | 5 | 66 | 475 | 86 |
| comp20 | Ing0506-2 | 121 | 19 | 5 | 5 | 78 | 691 | 185 |
| comp21 | Ing0304-2 | 94 | 18 | 5 | 5 | 78 | 463 | 129 |

ソース: https://www.eeecs.qub.ac.uk/itc2007/Login/SecretPage.php

### DDS-2008 (DDS1-7)

Di Gaspero, Schaerf らによるベンチマークセット（7問）。

| Instance | Name | Courses | Rooms | Days | Periods | Curricula | Unavail | RoomConstr |
|----------|------|---------|-------|------|---------|-----------|---------|------------|
| DDS1 | Bari-IIsem-2008 | 201 | 21 | 5 | 15 | 99 | 11948 | 3000 |
| DDS2 | Bolzano-Isem-2009 | 82 | 11 | 6 | 11 | 11 | 3414 | 502 |
| DDS3 | Roma1-IIsem-2008 | 50 | 8 | 5 | 11 | 9 | 1102 | 52 |
| DDS4 | Salerno-IIsem-2008 | 217 | 31 | 5 | 10 | 105 | 925 | 1931 |
| DDS5 | Lettere-IIsem-2008 | 109 | 18 | 6 | 12 | 44 | 2656 | 975 |
| DDS6 | Ing0708-2 | 107 | 17 | 5 | 5 | 62 | 589 | 140 |
| DDS7 | TestUD | 49 | 9 | 6 | 10 | 37 | 405 | 128 |

### Test (toy, test1-4)

テスト用の小規模インスタンス（5問）。

| Instance | Courses | Rooms | Days | Periods | Curricula | Unavail | RoomConstr |
|----------|---------|-------|------|---------|-----------|---------|------------|
| toy | 4 | 3 | 5 | 4 | 2 | 8 | 3 |
| test1 | 46 | 12 | 5 | 4 | 26 | 20 | 109 |
| test2 | 52 | 12 | 5 | 4 | 30 | 148 | 128 |
| test3 | 56 | 13 | 5 | 4 | 55 | 229 | 159 |
| test4 | 55 | 10 | 5 | 5 | 55 | 299 | 115 |

### Erlangen (erlangen2011_2 - erlangen2014_1)

Friedrich-Alexander University Erlangen-Nürnberg の実データ（6問）。大規模インスタンス。

| Instance | Courses | Rooms | Days | Periods | Curricula | Unavail | RoomConstr |
|----------|---------|-------|------|---------|-----------|---------|------------|
| erlangen2011_2 | 755 | 176 | 5 | 6 | 1949 | 7276 | 107217 |
| erlangen2012_1 | 764 | 110 | 5 | 6 | 3442 | 6283 | 55528 |
| erlangen2012_2 | 850 | 132 | 5 | 6 | 3691 | 7780 | 78628 |
| erlangen2013_1 | 738 | 137 | 5 | 6 | 3286 | 7011 | 73641 |
| erlangen2013_2 | 705 | 140 | 5 | 6 | 3503 | 6223 | 69957 |
| erlangen2014_1 | 730 | 137 | 5 | 6 | 3075 | 6029 | 72244 |

### Udine (Udine1-9)

University of Udine の実データ（9問）。

| Instance | Name | Courses | Rooms | Days | Periods | Curricula | Unavail | RoomConstr |
|----------|------|---------|-------|------|---------|-----------|---------|------------|
| Udine1 | Ing0809-1 | 142 | 21 | 5 | 5 | 83 | 841 | 426 |
| Udine2 | Ing0809-2 | 152 | 21 | 5 | 5 | 82 | 916 | 456 |
| Udine3 | Ing0708-2 | 107 | 17 | 5 | 5 | 62 | 635 | 2 |
| Udine4 | Ing0708-3 | 62 | 16 | 5 | 5 | 55 | 469 | 122 |
| Udine5 | Ing0910-1 | 141 | 21 | 5 | 5 | 74 | 174 | 424 |
| Udine6 | Ing1213-1 | 127 | 21 | 5 | 5 | 54 | 893 | 127 |
| Udine7 | Ing1112-1 | 130 | 22 | 5 | 5 | 54 | 767 | 260 |
| Udine8 | Ing1112-2 | 140 | 23 | 5 | 5 | 101 | 821 | 280 |
| Udine9 | Ing1011-1 | 122 | 21 | 5 | 5 | 71 | 833 | 367 |

### EasyAcademy (EA01-12)

EasyAcademy からのベンチマークセット（12問）。

| Instance | Courses | Rooms | Days | Periods | Curricula | Unavail | RoomConstr |
|----------|---------|-------|------|---------|-----------|---------|------------|
| EA01 | 134 | 27 | 5 | 5 | 37 | 82 | 1 |
| EA02 | 54 | 13 | 5 | 10 | 22 | 919 | 129 |
| EA03 | 145 | 65 | 5 | 11 | 65 | 3207 | 1350 |
| EA04 | 136 | 29 | 5 | 11 | 29 | 1 | 1 |
| EA05 | 134 | 25 | 5 | 7 | 22 | 505 | 1309 |
| EA06 | 50 | 15 | 5 | 10 | 19 | 762 | 2 |
| EA07 | 159 | 51 | 5 | 10 | 61 | 1134 | 938 |
| EA08 | 123 | 14 | 5 | 10 | 23 | 62 | 1 |
| EA09 | 154 | 36 | 5 | 5 | 63 | 833 | 954 |
| EA10 | 50 | 8 | 6 | 12 | 47 | 1184 | 59 |
| EA11 | 72 | 14 | 5 | 6 | 27 | 537 | 167 |
| EA12 | 88 | 19 | 5 | 6 | 19 | 512 | 146 |

### UUMCAS (1問)

Universiti Utara Malaysia College of Arts and Sciences のデータ。

| Instance | Courses | Rooms | Days | Periods | Curricula | Unavail | RoomConstr |
|----------|---------|-------|------|---------|-----------|---------|------------|
| UUMCAS_A131 | 247 | 32 | 5 | 18 | 172 | 1482 | 0 |

## 参考文献

- Di Gaspero, L., McCollum, B., & Schaerf, A. (2007). *The Second International Timetabling Competition (ITC-2007): Curriculum-based Course Timetabling (Track 3)*. Technical Report, Queen's University Belfast.
  - 問題定義: https://www.eeecs.qub.ac.uk/itc2007/curriculmcourse/report/curriculumtechreport.pdf
  - 入力フォーマット: https://www.eeecs.qub.ac.uk/itc2007/curriculmcourse/course_curriculm_index_files/Inputformat.htm
  - 出力フォーマット: https://www.eeecs.qub.ac.uk/itc2007/curriculmcourse/course_curriculm_index_files/outputformat.htm
