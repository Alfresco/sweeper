"""
Author:
Martin Whittington martin.whittington@alfresco.com
==================================================
Repo: https://github.com/Alfresco/sweeper
==================================================
"""

#!/usr/bin/python
from __future__ import print_function
from os import environ
from os.path import expanduser
import sys
import datetime
import yaml
import boto3
from botocore.exceptions import ProfileNotFound, ClientError

def print_banner():
    """
    Prints a welcome banner
    """
    print(" _______           _______  _______  _______  _______  _______")
    print("(  ____ \|\     /|(  ____ \(  ____ \(  ____ )(  ____ \(  ____ )")
    print("| (    \/| )   ( || (    \/| (    \/| (    )|| (    \/| (    )|")
    print("| (_____ | | _ | || (__    | (__    | (____)|| (__    | (____)|")
    print("(_____  )| |( )| ||  __)   |  __)   |  _____)|  __)   |     __)")
    print("      ) || || || || (      | (      | (      | (      | (\ (   ")
    print("/\____) || () () || (____/\| (____/\| )      | (____/\| ) \ \__")
    print("\_______)(_______)(_______/(_______/|/       (_______/|/   \__/")
    print("_______________________________________________________________")

def show_usage():
    """
    Describes Sweeper usage
    """
    print("=====================================================")
    print("usage: python Sweeper.py -p <profile> [ -h ]")
    print(" options:")
    print("  -c <config file>, Yaml config file to load (loads default found in root file if not provided)")
    print("  -p <profile(s)>, AWS Profile(s) to use from credentials file. If ommited, Sweeper will use env vars. For more profile, pass a csv list (default1,default2)")
    print("  -o <file name>, Outputs results into a text file instead of std out")
    print("  -h, displays this usage")
    sys.exit()

class Sweeper(object):
    """
    Sweeper class object
    """
    def __init__(self, args):
        # Sensible class defaults
        self.profile_list = []
        self.current_profile = ''
        self.regions_to_exclude = []
        self.checks_to_exclude = []
        self.regions = [
            'us-east-1',
            'us-east-2',
            'us-west-1',
            'us-west-2',
            'ca-central-1',
            'ap-south-1',
            'ap-northeast-1',
            'ap-northeast-2',
            'ap-southeast-1',
            'ap-southeast-2',
            'eu-central-1',
            'eu-west-1',
            'eu-west-2',
            'sa-east-1'
        ]
        self.config_location = './config.yml'
        self.output_file = False
        self.message = ''

        # Function calls
        self.set_config_file(args)
        self.set_output(args)
        self.load_file()
        self.set_profile(args)
        self.run_sweeper(args)

    def set_config_file(self, args):
        """
        Sets the config_location if the arg is passed
        """
        if '-c' in args:
            self.config_location = str(args['-c'])
        else:
            print("WARN: Config option not provided. Using config.yml found in root")

    def set_output(self, args):
        """
        Sets whether to output to a file or not
        """
        if '-o' in args:
            self.output_file = True

    def set_profile(self, args):
        """
        Sets the correct profile to use.
        :param args: List of arguments
        """
        if '-p' in args:
            # Profile provided. Is there a valid aws creds file installed?
            # Overwrites profiles found in config.yml
            if self.profile_list:
                print("WARN: Overriding profiles found in config.yml")
            try:
                home = expanduser("~")
                creds_file = open("{}/.aws/credentials".format(home))
                creds_file.close()
                if ',' in str(args['-p']):
                    # Multiple profiles
                    self.profile_list = str(args['-p']).split(',')
                else:
                    self.profile_list = [str(args['-p'])]
            except IOError:
                print("ERROR: AWS Credentials file not found. Please run 'aws configure' first")
                sys.exit(1)
        elif self.profile_list:
            # Profiles not provided but have been loaded from config file
            config_file = 'config.yml'
            if '-c' in args:
                config_file = args['-c']
            print("Using profiles found in {}: {}".format(config_file, self.profile_list))
        else:
            # Profile not provided either in config or cli. Use env vars, if set
            if "AWS_ACCESS_KEY_ID" in environ and "AWS_SECRET_ACCESS_KEY" in environ:
                print("Using AWS environment variables for the current session")
            else:
                print("ERROR: Unable to authenticate with AWS")
                print(" Either run 'aws configure', set your AWS Environment Variables")
                print(" Or set some profiles to run against in the config file or cmd line")
                sys.exit(1)

    def load_file(self):
        """
        Loads the *.yml file from either the args or local default
        """
        # First, lets read the YAML file and parse what we need
        with open(self.config_location) as stream:
            try:
                params = yaml.load(stream)
                if 'regions_to_exclude' in params:
                    for r in params['regions_to_exclude']:
                        if r in self.regions:
                            self.regions.remove(r)

                if 'checks_to_exclude' in params:
                    self.checks_to_exclude = params['checks_to_exclude']
                else:
                    print("WARN: Excludes not found in the config file. All services will be checked")

                if 'profiles' in params:
                    self.profile_list = params['profiles']

            except yaml.YAMLError as err:
                print(str(err))
                sys.exit(1)

    def create_client(self, service, region):
        """
        Sets up the current session object needed to perform the API calls
        """
        if self.current_profile:
            session = boto3.Session(
                profile_name=self.current_profile,
                region_name=region
            )
            return session.client(service)
        else:
            return boto3.client(service, region_name=region)

    def output(self, string):
        """
        Determines how to output the results
        """
        if self.output_file:
            self.message += string
            self.message += '\n'
        else:
            print(string)

    def check_elbs(self):
        """
        Uses the API's to check for orphaned ELB's
        """
        try:
            for region in self.regions:
                client = self.create_client('elb', region)
                self.output("\nChecking for orphaned ELB's in {}".format(region))
                self.output("This sweep looks for ELB's without any attached instances.")
                self.output("==========================================================")
                response = client.describe_load_balancers()
                for elb in response['LoadBalancerDescriptions']:
                    if not elb['Instances']:
                        self.output("{} does not have any instances attached".format(elb['LoadBalancerName']))
                self.output("ELB sweep in {} complete".format(region))
                self.output("All configured regions checked for orphaned ELB's")
        except ClientError:
            self.output("Your AWS profile does not have access. Please fix this and try again\n")

    def check_ebs_volumes(self):
        """
        Uses the API's to check for unattached volumes.
        #TODO currently max 500 results
        """
        try:
            for region in self.regions:
                self.output("\nChecking for unattached EBS Volumes in {}".format(region))
                self.output("==========================================================")
                client = self.create_client('ec2', region)
                response = client.describe_volumes()
                for volume in response['Volumes']:
                    if not volume['Attachments']:
                        self.output("{} does not have any attachments".format(volume['VolumeId']))
                self.output("Volume sweep in {} complete".format(region))
                self.output("All configured regions checked for unattached EBS volumes")
        except ClientError:
            self.output("Your AWS profile does not have access. Please fix this and try again\n")

    def check_snapshots(self):
        """
        Checks if snapshots are paired to AMI's
        """
        try:
            for region in self.regions:
                snapshot_list = []
                self.output("\nChecking for unused snapshots in {}".format(region))
                self.output("**WARNING: This can take along time. Please use with caution**")
                self.output("==========================================================")
                client = self.create_client('ec2', region)
                snapshots = client.describe_snapshots(
                    Filters=[
                        {
                            'Name':'status',
                            'Values': [
                                'completed'
                            ]
                        }
                    ]
                )
                images = client.describe_images(
                    Filters=[
                        {
                            'Name':'state',
                            'Values': [
                                'available'
                            ]
                        }
                    ]
                )
                for snapshot in snapshots['Snapshots']:
                    snapshot_id = snapshot['SnapshotId']
                    snapshot_found = False
                    for image in images['Images']:
                        if 'BlockDeviceMappings' in image:
                            for mapping in image['BlockDeviceMappings']:
                                if 'Ebs' in mapping:
                                    if 'SnapshotId' in mapping['Ebs']:
                                        snapshot_found = mapping['Ebs']['SnapshotId'] == snapshot_id
                    if not snapshot_found:
                        snapshot_list.append(snapshot_id)
                self.output("There are {} snapshots to remove".format(len(snapshot_list)))
                if self.output_file:
                    for snap in snapshot_list:
                        self.output(snap)
                self.output("Snapshot sweep complete in {}".format(region))
        except ClientError:
            self.output("Your AWS profile does not have access. Please fix this and try again\n")

    def check_eips(self):
        """
        Checks if EIPS arent attached to an instance
        """
        try:
            for region in self.regions:
                self.output("\nChecking for unattached EIP's in {}".format(region))
                self.output("==========================================================")
                client = self.create_client('ec2', region)
                response = client.describe_addresses()
                for address in response['Addresses']:
                    if 'InstanceId' not in address:
                        self.output("{} is not attached to any instance.".format(address['PublicIp']))
                self.output("EIP sweep complete in {}".format(region))
        except ClientError:
            self.output("Your AWS profile does not have access. Please fix this and try again\n")

    def check_beanstalk_environments(self):
        """
        Checks for ElasticBeanstalk environments and if they are still running. These
        environments can incur a cost as they are designed to be highly available
        """
        try:
            for region in self.regions:
                self.output("\nChecking for Beanstalk environments still running in {}".format(region))
                self.output("This checks for environments which will keep services running at a cost")
                self.output("==========================================================")
                client = self.create_client('elasticbeanstalk', region)
                response = client.describe_environments(
                    IncludeDeleted=False
                )
                for environment in response['Environments']:
                    self.output("{} is still running. Did you know this?".format(environment['EnvironmentName']))
                self.output("ElasticBeanstalk sweep complete in {}".format(region))
        except ClientError:
            self.output("Your AWS profile does not have access. Please fix this and try again\n")

    def check_opsworks(self):
        """
        Checks all running services managed by Opsworks.
        """
        try:
            for region in self.regions:
                self.output("\nChecking for Opsworks provisioned resources in {}".format(region))
                self.output("Opsworks has self-healing functionality that potentially could have")
                self.output("healed a service that you destroyed elsewhere.")
                self.output("==========================================================")
                client = self.create_client('opsworks', region)
                response = client.describe_stacks()
                for stack in response['Stacks']:
                    # first list any ecs clusters
                    stack_id = stack['StackId']
                    self.output("Checking {} for services. Information gathering for action.".format(stack_id))
                    # ECS
                    ecs = client.describe_ecs_clusters(
                        StackId=stack_id
                    )
                    self.output("{} has {} running ECS Clusters".format(stack_id, len(ecs['EcsClusters'])))
                    # EIP
                    eip = client.describe_elastic_ips(
                        StackId=stack_id
                    )
                    self.output("{} has {} EIP's".format(stack_id, len(eip['ElasticIps'])))
                    # EC2 Instances
                    instances = client.describe_instances(
                        StackId=stack_id
                    )
                    self.output("{} has {} Ec2 instances running".format(
                        stack_id,
                        len(instances['Instances']))
                    )
                    # ELB
                    elbs = client.describe_elastic_load_balancers(
                        StackId=stack_id
                    )
                    self.output("{} has {} ELB's running".format(stack_id, len(elbs['ElasticLoadBalancers'])))
                    # RDS
                    rds = client.describe_rds_db_instances(
                        StackId=stack_id
                    )
                    self.output("{} has {} RDS instances running".format(
                        stack_id,
                        len(rds['RdsDbInstances']))
                    )
                    # EBS
                    ebs = client.describe_volumes(
                        StackId=stack_id
                    )
                    self.output("{} has {} EBS Volumes registered".format(stack_id, len(ebs['Volumes'])))

                self.output("Opsworks sweep complete in {}".format(region))
        except ClientError:
            self.output("Your AWS profile does not have access. Please fix this and try again\n")

    def run_checks(self, profile=None):
        """
        Wrapper function that runs the checks we need
        """
        self.output("==========================================================")
        self.output('\nSweeping AWS profile ({})'.format(profile))
        self.output("==========================================================")
        if profile:
            self.current_profile = profile
        try:
            if 'elb' not in self.checks_to_exclude:
                self.check_elbs()
            if 'ebs-volumes' not in self.checks_to_exclude:
                self.check_ebs_volumes()
            if 'ebs-snapshots' not in self.checks_to_exclude:
                self.check_snapshots()
            if 'ec2-eips' not in self.checks_to_exclude:
                self.check_eips()
            if 'elastic-beanstalk' not in self.checks_to_exclude:
                self.check_beanstalk_environments()
            if 'opsworks' not in self.checks_to_exclude:
                self.check_opsworks()
            # TODO add s3 checks. Buckets that havent been access in n days. Are they still used?
            # TODO more checks!
        except ProfileNotFound:
            self.output("AWS profile ({}) could not be found".format(self.current_profile))
            if not isinstance(self.profile_list, list):
                sys.exit(1)
            else:
                pass

    def run_sweeper(self, args):
        """
        Runs the sweeper based on the profile passed in and the config settings
        """
        if not self.output_file:
            print("Sweeping to screen")
        else:
            print("Sweeping to {}".format(args['-o']))

        self.output('Current Time {:%Y-%b-%d %H:%M:%S}'.format(datetime.datetime.now()))
        for profile in self.profile_list:
            self.run_checks(profile)

        if self.output_file:
            results = open(args['-o'], 'w')
            results.write(self.message)
            results.close()
        self.output("Sweeper is complete!")
        sys.exit(0)

if __name__ == '__main__':
    # Get the args, pass them in or default them or fail
    opts = {}
    while sys.argv:
        if sys.argv[0] == '-h':
            show_usage()
        elif sys.argv[0][0] == '-':
            opts[sys.argv[0]] = sys.argv[1]
        sys.argv = sys.argv[1:]
    print_banner()
    Sweeper(opts)
