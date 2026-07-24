variable "environment" {}
variable "vpc_id" {}
variable "subnet_ids" {}
variable "db_instance_class" {}

resource "aws_db_subnet_group" "main" {
  name       = "aios-${var.environment}-db-subnet-group"
  subnet_ids = var.subnet_ids
}

resource "aws_db_instance" "main" {
  identifier           = "aios-${var.environment}-db"
  engine               = "postgres"
  engine_version       = "16"
  instance_class       = var.db_instance_class
  allocated_storage    = 100
  storage_type         = "gp3"
  db_subnet_group_name = aws_db_subnet_group.main.name
  skip_final_snapshot  = true
  
  username = "aios_admin"
  password = "CHANGE_ME_VIA_SECRETS_MANAGER"
}
