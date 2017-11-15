# Sweeper

## Description
A tool that sweeps your AWS account for still running or orphaned services that may be costing you money. The tool doesn't destroy them, it only informs you of what is running. This tool takes its inspiration from the ["Avoiding Unexpected Charges"](http://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/checklistforunwantedcharges.html) checklist.

## Features
- Runs a report based on still running services in your AWS accounts
- Highlights potential cost saving resources that could be removed

## Requirements
Please ensure you have Python running locally. 2.x or 3.x should work fine.
Before running please install the boto3 libraries either globally or locally.

Globally:
```
pip install boto3
```
Locally:
```
pip install boto3 -t .
```
Please also ensure that `aws configure` has been performed. It isn't an essential command but allows for multiple AWS accounts to be checked

## Configuration
The configuration file `config.yml` contains three current sections; `regions_to_exclude`,`checks_to_exclude` and `profiles`. In the `regions_to_exclude` section, populate it with a list of regions that you do not want to check as part of the sweep.
The `checks_to_exclude` section, populate it with a list of checks to skip e.g. `elb` or `opsworks`. An example has been included in this repo.
The `profiles` section should include the name of profiles you wish to check. These name should be found in your `~/.aws/credentials` file

## Usage
```
python Sweeper.py
```
This will run Sweeper using the default config file. If you do not provide the `profiles` config parameters Sweeper will look for AWS credentials in your environment variables
```
python Sweeper.py -c <config>
```
This will run Sweeper using a specified config file, not the default.
```
python Sweeper.py -p <profile(s)>
```
This will run Sweeper with an AWS profile or profiles. These profiles can be found in your credentials file. If you want to check more than one profile, provide a csv list of profiles e.g. `python Sweeper.py -p default1,default2`
```
python Sweeper.py -o <output file>
```
This will run Sweeper and output the results into a text file with the name of your choice e.g. `python Sweeper.py -o results.txt` 

## Future changes
- Extra checks to be added (S3)
- Use instance profiles if running on an Ec2 instance
- Appropriate use of roles when running in a Lambda

## Develop
Work in progress will be on the `Develop` branch. If you want to use the latest improvements, use this branch. All releases are tagged from the `Master` branch

## Contribution Guidelines
Please fork from Develop. Any forks to Master will be ignored. Raise a PR and the code will be reviewed in time. I will routinely merge from Develop to Master with new features that are in the Develop branch
