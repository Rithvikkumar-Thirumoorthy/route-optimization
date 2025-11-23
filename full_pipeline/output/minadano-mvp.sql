--- RD name and distributorname matched
with cte as (
SELECT DISTINCT 
    N.DistributorID,
	D.DistributorName as DName
FROM nodetree N
INNER JOIN salesagent S ON N.SalesmanTerritory = S.Code
INNER JOIN customer C ON S.Code = C.SalesAgent
INNER JOIN Barangay ON Barangay.Code = C.Address3
inner join Distributor D on D.DistributorID=N.DistributorID
WHERE C.Active = 1 and N.DistributorID='11619')
select Count(tdlinx) from prospective p 
inner join Cte C on P.rd=c.DName
where C.DistributorID='11619' 
Group by C.DistributorID

--  (BarangayCode and BarangayCode matched) and (RD name and distributorname matched)
 
with cte as (
SELECT DISTINCT 
    N.DistributorID,
    Barangay.Code AS BarangayCode,
	D.DistributorName as DName
FROM nodetree N
INNER JOIN salesagent S ON N.SalesmanTerritory = S.Code
INNER JOIN customer C ON S.Code = C.SalesAgent
INNER JOIN Barangay ON Barangay.Code = C.Address3
inner join Distributor D on D.DistributorID=N.DistributorID
WHERE C.Active = 1 and N.DistributorID='11619')
select Count(tdlinx) from prospective p 
inner join Cte C on C.BarangayCode=P.Barangay_Code and P.rd=c.DName 
where C.DistributorID='11619'
Group by C.DistributorID -- 235





--- RD name and distributorname matched
with cte as (
SELECT DISTINCT 
    N.DistributorID,
	D.DistributorName as DName
FROM nodetree N
INNER JOIN salesagent S ON N.SalesmanTerritory = S.Code
INNER JOIN customer C ON S.Code = C.SalesAgent
INNER JOIN Barangay ON Barangay.Code = C.Address3
inner join Distributor D on D.DistributorID=N.DistributorID
WHERE C.Active = 1 and N.DistributorID='11619')
select Count(distinct barangay_code) from prospective p 
inner join Cte C on P.rd=c.DName 
where C.DistributorID='11619' 
Group by C.DistributorID  -- 628
 
--  (BarangayCode and BarangayCode matched) and (RD name and distributorname matched)
 
with cte as (
SELECT DISTINCT 
    N.DistributorID,
    Barangay.Code AS BarangayCode,
	D.DistributorName as DName
FROM nodetree N
INNER JOIN salesagent S ON N.SalesmanTerritory = S.Code
INNER JOIN customer C ON S.Code = C.SalesAgent
INNER JOIN Barangay ON Barangay.Code = C.Address3
inner join Distributor D on D.DistributorID=N.DistributorID
WHERE C.Active = 1 and N.DistributorID='11619')
select Count(distinct barangay_code) from prospective p 
inner join Cte C on C.BarangayCode=P.Barangay_Code and P.rd=c.DName 
where C.DistributorID='11619'
Group by C.DistributorID -- 235
 
 
--  (BarangayCode and BarangayCode matched) and (RD name and distributorname not matched)
 
with cte as (
SELECT DISTINCT 
    N.DistributorID,
    Barangay.Code AS BarangayCode,
	D.DistributorName as DName
FROM nodetree N
INNER JOIN salesagent S ON N.SalesmanTerritory = S.Code
INNER JOIN customer C ON S.Code = C.SalesAgent
INNER JOIN Barangay ON Barangay.Code = C.Address3
inner join Distributor D on D.DistributorID=N.DistributorID
WHERE C.Active = 1 and N.DistributorID='11619')
select Count(distinct barangay_code) from prospective p 
inner join Cte C on C.BarangayCode=P.Barangay_Code and P.rd<>c.DName 
where C.DistributorID='11619'
Group by C.DistributorID -- 11
 --  (RD name and distributorname  matched) and (BarangayCode and BarangayCode not matched)  
 
with cte as (
SELECT DISTINCT 
    N.DistributorID,
    Barangay.Code AS BarangayCode,
	D.DistributorName as DName
FROM nodetree N
INNER JOIN salesagent S ON N.SalesmanTerritory = S.Code
INNER JOIN customer C ON S.Code = C.SalesAgent
INNER JOIN Barangay ON Barangay.Code = C.Address3
inner join Distributor D on D.DistributorID=N.DistributorID
WHERE C.Active = 1 and N.DistributorID='11619')
select Count(distinct barangay_code) from prospective p 
inner join Cte C on P.rd=c.DName and  C.BarangayCode<>P.Barangay_Code 
where C.DistributorID='11619' 
Group by C.DistributorID -- 628
