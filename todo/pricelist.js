var rp = require('request-promise');
const fetch = require('node-fetch');
require('custom-env').env();
var fs = require('fs');

const path = './pricelist.json'

// try {
//     fs.unlinkSync(path)
//     //file removed
// } catch (err) {
//     console.error(err)
// }

function pullPricing() {
    var options = {
        method: 'POST',
        uri: process.env.API_URL,
        formData: {
            Key: process.env.API_KEY,
            Operation: 'GetEntities',
            Entity: 'product',
            Filter: `producttypecode<eq>4 OR producttypecode<eq>2`,
            Attributes: 'name, productid, price, producttypecode'
        }

    }
    rp(options).then(function (body) {

        var data = JSON.parse(body);

        data = data.Data

        const modifiedData = data.map(function (data) {

            console.log(data);

            return data;
        });

        var stringData = JSON.stringify(modifiedData);

        fs.writeFile('pricelist.json', stringData, (err) => {
            if (err) throw err;
            console.log('The file has been saved!');
        });

    });

}

pullPricing();