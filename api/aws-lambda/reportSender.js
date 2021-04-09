var aws = require("aws-sdk");
var ses = new aws.SES({ region: "us-east-1" });


exports.handler = async function (event) {
    const source = "";
    event.Records.forEach(async (record) => {
        const destination = record.dynamodb.NewImage.emailId.S;
        const link = record.dynamodb.NewImage.docLink.S;
        var params = {
            Destination: {
                ToAddresses: [destination],
            },
            Message: {
                Body: {
                    Text: { Data: "Your Lecturizer generated lecture report link : " + link },
                },

                Subject: { Data: "Lecturizer Report" },
            },
            Source: source,
        }
        console.log(params);
        await ses.sendEmail(params).promise();
    });
};