var rp = require('request-promise');
var _ = require('lodash');
const prompt = require('prompt-sync')();
const fetch = require('node-fetch');
var moment = require('moment');
var moment = require('moment-timezone');
require('custom-env').env();
var fs = require('fs');

pushClasses();

async function pushClasses() {

    const classGuid = prompt('Class GUID: ');

    console.log(classGuid);

    var pullClasses = new Promise(function (resolve, reject) {
        var options = {
            method: 'POST',
            uri: process.env.API_URL,
            formData: {
                Key: process.env.API_KEY,
                Operation: 'GetEntity',
                Entity: 'cobalt_class',
                Guid: classGuid,
                Attributes: 'cobalt_classbegindate,cobalt_classenddate,cobalt_classid,cobalt_locationid,cobalt_name,cobalt_description,cobalt_locationid,cobalt_cobalt_tag_cobalt_class/cobalt_name,cobalt_fullday,cobalt_publishtoportal,statuscode,cobalt_cobalt_classinstructor_cobalt_class/cobalt_name,cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_productid,cobalt_cobalt_class_cobalt_classregistrationfee/statuscode,cobalt_outsideprovider,cobalt_outsideproviderlink'
            }

        }
        rp(options).then(function (body) {

            var body = JSON.parse(body);

            var data = body.Data

            console.log(data);

            var start = moment.tz(data.cobalt_ClassBeginDate.Display, 'Etc/GMT');
            var end = moment.tz(data.cobalt_ClassEndDate.Display, 'Etc/GMT');

            data.cobalt_ClassBeginDate.Display = start.tz('America/New_York').format('YYYY-MM-DD HH:mm:SS');
            data.cobalt_ClassEndDate.Display = end.tz('America/New_York').format('YYYY-MM-DD HH:mm:SS');

            var orderId = data.cobalt_cobalt_class_cobalt_classregistrationfee.map(function (data) {

                var orderObject = {
                    "id" : data.cobalt_productid.Value,
                    "status" : data.statuscode.Value
                }

                return orderObject;

            });

            var prices = fs.readFileSync('./pricelist.json', { encoding: 'utf8', flag: 'r' });

            prices = JSON.parse(prices);

            orderId = _.filter(orderId, (o) => o.id !== '8d6bb524-f1d8-41ad-8c21-ae89d35d4dc3');

            orderId = _.filter(orderId, (o) => o.id !== 'c3102913-ffd4-49d6-9bf6-5f0575b0b635');
            
            orderId = _.filter(orderId, (o) => o.id !== null);

            orderId = _.filter(orderId, (o) => o.status === 1);

            // console.log(orderId);
            // console.log(orderId.length);

            if (orderId.length > 0) {

                var cost = prices.filter(function (price) {

                    //console.log(orderId[0]);

                    if (price.ProductId === orderId[0].id) {
                        //console.log(price.Price);
                        return price;
                    }

                });

                // console.log(data.cobalt_classId);
                // console.log(cost);

                data.cobalt_price = cost[0].Price;

            } else {
                data.cobalt_price = '0.0000';
            }

            data.cobalt_price = data.cobalt_price.slice(0, -2);

            console.log(data.cobalt_price);

            if(data.cobalt_OutsideProvider === 'true'){
                data.cobalt_price = ' ';
            }

            const tags = data.cobalt_cobalt_tag_cobalt_class.map(function (data) {

                var tags = {
                    name: data.cobalt_name
                }

                return data.cobalt_name;
            });

            data.statuscode = data.statuscode.Display;

            if (data.statuscode === 'Inactive' || data.cobalt_PublishtoPortal === 'false') {

                data.publish = true;
            } else if (data.statuscode === 'Active' && data.cobalt_PublishtoPortal === 'true') {

                data.publish = false;

            } else {

                data.publish = true;

            }

            if (data.cobalt_fullday === 'true') {

                data.all_day = true;

            } else {

                data.all_day = false;

            }


            switch (data.cobalt_LocationId.Display) {
                case "MIAMI HQ":
                    data.cobalt_name = `<span style="color:#798e2d;">${data.cobalt_name}</span>`;
                    data.locationId = 4694;
                    break;

                case "West Broward - Sawgrass Office":
                    data.cobalt_name = `<span style="color:#0082c9;">${data.cobalt_name}</span>`;
                    data.locationId = 4698;
                    break;

                case "Coral Gables Office":
                    data.cobalt_name = `<span style="color:#633e81;">${data.cobalt_name}</span>`;
                    data.locationId = 4696;
                    break;

                case "JTHS - MIAMI Training Room (Jupiter)":
                    data.cobalt_name = `<span style="color:#005962;">${data.cobalt_name}</span>`;
                    data.locationId = 4718;
                    break;

                case "Northwestern Dade":
                    data.cobalt_name = `<span style="color:#9e182f;">${data.cobalt_name}</span>`;
                    data.locationId = 4735;
                    break;

                case "Northwestern Dade Office":
                    data.cobalt_name = `<span style="color:#9e182f;">${data.cobalt_name}</span>`;
                    data.locationId = 4735;
                    break;

                case "NE Broward Office-Ft. Lauderdale":
                    data.cobalt_name = `<span style="color:#f26722;">${data.cobalt_name}</span>`;
                    data.locationId = 4702;
                    break;

                case "Aventura Office":
                    data.cobalt_name = `<span style="color:#000000;">${data.cobalt_name}</span>`;
                    data.locationId = 22099;
                    break;

                default:
                    data.cobalt_name = data.cobalt_name;
            }

            //console.log(data.cobalt_LocationId.Display);
            //console.log(data.cobalt_LocationId.Value);

            if(data.cobalt_OutsideProvider === 'true'){
                data.cobalt_Description = `${data.cobalt_Description}<br><input style="background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;" type="button" value="Register Now" onclick="window.location.href='${data.cobalt_OutsideProviderLink}'" />`
            }else{
                data.cobalt_Description = `${data.cobalt_Description}<br><input style="background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;" type="button" value="Register Now" onclick="window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D${data.cobalt_classId}'" />`
            }

            if (data.cobalt_cobalt_classinstructor_cobalt_class.length > 0) {

                //console.log(data.cobalt_cobalt_classinstructor_cobalt_class);

                const classInstructor = data.cobalt_cobalt_classinstructor_cobalt_class.map(function (data) {

                    return data.cobalt_name;

                });

                //console.log(classInstructor[0]);

                data.cobalt_Description = `<p style="font-weight:bold;color: black;">Instructor: ${classInstructor[0]}</p><br><br>${data.cobalt_Description}`

                //console.log(data.cobalt_Description);

            } else {

                data.cobalt_Description = `${data.cobalt_Description}`

                //console.log(data.cobalt_Description);

            }

            data.cobalt_name = data.cobalt_name;

            data.cobalt_cobalt_tag_cobalt_class = tags;

            fs.appendFile('logs/apiData.json', `[${moment().format('h:mm:ss a')}] ${JSON.stringify(data)} \n`, (err) => {
                if (err) throw err;
            })

            //console.log(data);

            resolve(data);

        })
            .catch(function (err) {
                reject(`Error: ${err}`);
            });
    });

    var data = await pullClasses;

    //console.log(data);
    
    var featuredClasses = [];
    var existingClasses = [];
    var newClasses = [];

    var checkIfExists = new Promise(function (resolve, reject) {

        setTimeout(function () {
            fetch(`${process.env.WORDPRESS_URL}/by-slug/${data.cobalt_classId}`)
                .then(res => res.json())
                .then(function(json){
                    resolve(json);
                });
        }, 1000)

    });

    var response = await checkIfExists;

    //console.log(response);

    if (Number.isInteger(response.id)) {

        const responseTags = response.tags.map(function (data) {

            return data.name;

        });
        
        var allTags = data.cobalt_cobalt_tag_cobalt_class.concat(responseTags);

        console.log(response.url);

        //console.log(data[0].cobalt_cobalt_tag_cobalt_class);
        //console.log(responseTags);
        //console.log(allTags);

        var filteredTags = allTags.filter((a, b) => allTags.indexOf(a) === b);

        if (response.image.url === undefined){

            data.cobalt_cobalt_tag_cobalt_class = filteredTags;
            console.log(`No class image!`);
            existingClasses.push(data);

        }else {

            data.cobalt_cobalt_tag_cobalt_class = filteredTags;
            data.featuredImage = response.image.url;
            console.log(response.image.url);
            featuredClasses.push(data);

        }

    } else {
        newClasses.push(data);
    }


    console.log(`Found ${existingClasses.length} existing classes and ${featuredClasses.length} featured classes, discarding ${newClasses.length} new classes.`);

    
    // console.log(newClasses);
    if (existingClasses.length > 0){
        modifyExistingClass(existingClasses);
    }else if(featuredClasses.length > 0){
        modifyFeaturedClass(featuredClasses);
    }
    

    function modifyExistingClass(data) {
        var ramcoClass = {
            "title": data[0].cobalt_name,
            "status": "publish",
            "hide_from_listings": data[0].publish,
            "description": data[0].cobalt_Description,
            "all_day": data[0].all_day,
            "start_date": data[0].cobalt_ClassBeginDate.Display,
            "end_date": data[0].cobalt_ClassEndDate.Display,
            "slug": data[0].cobalt_classId,
            "categories": data[0].cobalt_cobalt_tag_cobalt_class,
            "show_map_link": true,
            "show_map": true,
            "cost": data[0].cobalt_price,
            "tags": data[0].cobalt_cobalt_tag_cobalt_class,
            "venue": {
                "id": data[0].locationId
            }
        };

        fetch(`${process.env.WORDPRESS_URL}/by-slug/${data[0].cobalt_classId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: 'Basic ' + Buffer.from(process.env.WORDPRESS_CREDS).toString('base64')
            },
            body: JSON.stringify(ramcoClass)
        }).then(res => res.json()) // expecting a json response
            .then(body => console.log(body));
        console.log(`Class processed: ${data[0].cobalt_name}`);
    }

    function modifyFeaturedClass(data) {
        var ramcoClass = {
            "title": data[0].cobalt_name,
            "status": "publish",
            "hide_from_listings": data[0].publish,
            "description": data[0].cobalt_Description,
            "image": data[0].featuredImage,
            "all_day": data[0].all_day,
            "start_date": data[0].cobalt_ClassBeginDate.Display,
            "end_date": data[0].cobalt_ClassEndDate.Display,
            "slug": data[0].cobalt_classId,
            "categories": data[0].cobalt_cobalt_tag_cobalt_class,
            "show_map_link": true,
            "show_map": true,
            "cost": data[0].cobalt_price,
            "tags": data[0].cobalt_cobalt_tag_cobalt_class,
            "venue": {
                "id": data[0].locationId
            }
        };

        fetch(`${process.env.WORDPRESS_URL}/by-slug/${data[0].cobalt_classId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: 'Basic ' + Buffer.from(process.env.WORDPRESS_CREDS).toString('base64')
            },
            body: JSON.stringify(ramcoClass)
        }).then(res => res.json()) // expecting a json response
            .then(body => {

                if ("data" in body) {

                    //sendSlackMessage(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${data[i].cobalt_name} failed because of "${body.message}" \n`);

                    fs.appendFile('logs/results.json', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${data[0].cobalt_name} failed because of "${body.message}" \n`, (err) => {
                        if (err) throw err;
                    })

                } else {

                    //sendSlackMessage(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${data[i].cobalt_name} submitted successfully \n`);

                    fs.appendFile('logs/results.json', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${data[0].cobalt_name} submitted successfully \n ${body} \n`, (err) => {
                        if (err) throw err;
                    })

                }
            });
    }

}
