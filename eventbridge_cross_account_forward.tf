# Terraform module for cross-account or cross-region EventBridge S3 ObjectCreated event forwarding

variable "source_account_id" {
  description = "ID of the source AWS account where the S3 events originate"
  type        = string
}

variable "target_event_bus_arn" {
  description = "ARN of the target EventBridge event bus in the other account or region"
  type        = string
}

variable "rule_name" {
  description = "Name of the EventBridge rule"
  type        = string
  default     = "ForwardS3EventsCrossAccount"
}

resource "aws_iam_role" "eventbridge_put_events_role" {
  name = "EventBridgePutEventsRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "events.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_put_events_policy" {
  name = "EventBridgePutEventsPolicy"
  role = aws_iam_role.eventbridge_put_events_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = "events:PutEvents",
        Resource = var.target_event_bus_arn
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "forward_s3_events" {
  name        = var.rule_name
  description = "Forward S3 ObjectCreated events to another EventBridge bus"

  event_pattern = jsonencode({
    source = ["aws.s3"],
    detail = {
      eventName = ["PutObject", "CompleteMultipartUpload"],
      requestParameters = {
        bucketName = [{ "exists": true }]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "target_bus" {
  rule      = aws_cloudwatch_event_rule.forward_s3_events.name
  arn       = var.target_event_bus_arn
  role_arn  = aws_iam_role.eventbridge_put_events_role.arn
}