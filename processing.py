import logging
import gzip
import boto3
import time

logger = logging.getLogger()

def process_log_object(
    log_processing_rule, bucket, key, bucket_region, log_sinks,
    lambda_context, user_defined_annotations=None, session=None
):
    """
    Processes a CloudFront log object from S3 and sends each distinct field as a separate attribute to each sink.
    - Dynamically parses the header line for field names
    - Maps each log line to those names
    - Adds context and user annotations
    - Sends to sinks (e.g., Dynatrace) with all fields as columns
    """

    start_time = time.time()
    if not session:
        session = boto3.Session()

    if user_defined_annotations is None:
        user_defined_annotations = {}

    # Get the object from S3
    s3_client = session.client('s3')
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    body = obj['Body']

    # Handle gzip
    if key.endswith('.gz'):
        log_stream = gzip.GzipFile(fileobj=body)
    else:
        log_stream = body

    cloudfront_fields = []
    num_processed = 0
    for line in log_stream:
        if isinstance(line, bytes):
            line = line.decode('utf-8')
        line = line.strip()

        # Dynamically parse header for field names
        if line.startswith('#'):
            # Field definition line is "# Fields: ..."
            if line.lower().startswith("# fields:"):
                # Split after colon and strip/normalize
                cloudfront_fields = line.split(":", 1)[-1].strip().split()
                logger.debug(f"CloudFront fields parsed: {cloudfront_fields}")
            continue
        if not line or not cloudfront_fields:
            continue

        # Split log line into fields and map to names
        values = line.split('\t')
        log_entry = {}

        # Only map if the number of fields matches
        for idx, field_name in enumerate(cloudfront_fields):
            if idx < len(values):
                log_entry[field_name] = values[idx]
            else:
                log_entry[field_name] = None  # Fill missing values with None

        # Add context and annotations
        log_entry.update({
            "aws.s3.bucket.name": bucket,
            "aws.s3.key.name": key,
            "aws.region": bucket_region,
            "cloudfront_raw": line,  # Optionally keep original line
        })
        log_entry.update(user_defined_annotations)

        # Send to all sinks (each field is a separate column/attribute)
        for sink in log_sinks:
            sink.push(log_entry)

        num_processed += 1

        # Optionally: check remaining time for large files
        if num_processed % 1000 == 0 and hasattr(lambda_context, "get_remaining_time_in_millis"):
            if lambda_context.get_remaining_time_in_millis() < 10000:
                logger.warning(f"Not enough time left to process s3://{bucket}/{key}")
                break

    logger.info(f"Processed {num_processed} CloudFront log entries from s3://{bucket}/{key}")
    return num_processed
