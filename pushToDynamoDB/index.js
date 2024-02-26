const AWS = require('aws-sdk');
const fs = require('fs');

AWS.config.update({ region: 'us-east-1' }); // Replace YOUR_REGION with your AWS region
const dynamoDB = new AWS.DynamoDB.DocumentClient();
const tableName = 'yelp-restaurants'; // Replace YOUR_TABLE_NAME with your DynamoDB table name

const jsonData = fs.readFileSync('yelp-restaurants.json', 'utf8');
const items = JSON.parse(jsonData);

const putItemsToDynamoDB = async () => {
  for (const item of items) {
    item.timestamp = Date.now()
    const params = {
      TableName: tableName,
      Item: item,
    };

    try {
      await dynamoDB.put(params).promise();
      // console.log(`Successfully added item to DynamoDB: ${JSON.stringify(item)}`);
    } catch (error) {
      console.error(`Error adding item to DynamoDB: ${JSON.stringify(item)}`, error);
    }
  }
};

putItemsToDynamoDB();
