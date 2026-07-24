provider "aws" {
  region = var.aws_region
}

# --- VPC ---
module "vpc" {
  source = "./vpc"
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

# --- EKS Cluster ---
module "eks" {
  source       = "./eks"
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnets
  cluster_name = "aios-${var.environment}-cluster"
}

# --- RDS PostgreSQL ---
module "rds" {
  source             = "./rds"
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  db_instance_class  = var.db_instance_class
}

# --- Redis (ElastiCache) ---
module "redis" {
  source        = "./redis"
  environment   = var.environment
  vpc_id        = module.vpc.vpc_id
  subnet_ids    = module.vpc.private_subnets
  node_type     = var.redis_node_type
}
