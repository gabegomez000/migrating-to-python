var rp = require('request-promise');
const fetch = require('node-fetch');
var moment = require('moment');
var moment = require('moment-timezone');
var cron = require('node-cron');
require('custom-env').env();
var fs = require('fs');
var _ = require('lodash');

pushClasses();

async function pushClasses() {

    //const classGuid = prompt('Meeting GUID: ');

    //console.log(classGuid);

    dateStart = moment().subtract(1, 'hour').format("YYYY-MM-DD" + `T` + "HH" + `:00:00`);

    var pullClasses = new Promise(function (resolve, reject) {
        var options = {
            method: 'POST',
            uri: process.env.API_URL,
            formData: {
                Key: process.env.API_KEY,
                Operation: 'GetEntities',
                Entity: 'cobalt_meeting',
                Filter: `cobalt_BeginDate<ge>${dateStart} AND statuscode<eq>1`,
                Attributes: 'cobalt_BeginDate,cobalt_EndDate,cobalt_meetingId,cobalt_location,cobalt_name,cobalt_description,cobalt_cobalt_tag_cobalt_meeting/cobalt_name,cobalt_fullday,cobalt_publishtoportal,statuscode,cobalt_meeting_cobalt_meetingregistrationfees/cobalt_productid,cobalt_outsideprovider,cobalt_meeting_cobalt_meetingregistrationfees/statuscode,cobalt_meeting_cobalt_meetingregistrationfees/cobalt_publishtoportal,cobalt_outsideproviderlink'
            }

        }
        rp(options).then(function (body) {

            //console.log(body); 

            var data = JSON.parse(body);

            //console.log(data.ResponseCode); 

            if (data.ResponseCode === 404) {
                data = [];
            } else {
                data = data.Data
            }

            console.log(data);

            var modifiedData;

            //sendSlackMessage(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] Found ${data.length} classes. Prepping data for WordPress submit  \n`);
            console.log(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] Found ${data.length} classes. Prepping data for WordPress submit  \n`);
            fs.appendFile('logs/newClasses.log', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] Found ${data.length} classes. Prepping data for WordPress submit  \n`, (err) => {
                if (err) throw err;
            });



            if (data.length > 0) {


                modifiedData = data.map(function (data) {

                    console.log(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] Formatting ${data.cobalt_name}  \n`);

                    var start = moment.tz(data.cobalt_BeginDate.Display, 'Etc/GMT');
                    var end = moment.tz(data.cobalt_EndDate.Display, 'Etc/GMT');

                    data.cobalt_BeginDate.Display = start.tz('America/New_York').format('YYYY-MM-DD HH:mm:SS');
                    data.cobalt_EndDate.Display = end.tz('America/New_York').format('YYYY-MM-DD HH:mm:SS');

                    var orderId = data.cobalt_Meeting_Cobalt_MeetingRegistrationFees.map(function (data) {

                        var orderObject = {
                            "id": data.cobalt_productid.Value,
                            "status": data.statuscode.Value,
                            "portal": data.cobalt_PublishtoPortal
                        }

                        return orderObject;

                    });

                    console.log(data);

                    var prices = fs.readFileSync('./pricelist.json', { encoding: 'utf8', flag: 'r' });

                    prices = JSON.parse(prices);

                    orderId = _.filter(orderId, (o) => o.portal !== 'false');

                    orderId = _.filter(orderId, (o) => o.id !== '8d6bb524-f1d8-41ad-8c21-ae89d35d4dc3');

                    orderId = _.filter(orderId, (o) => o.id !== 'c3102913-ffd4-49d6-9bf6-5f0575b0b635');

                    orderId = _.filter(orderId, (o) => o.id !== 'd4af83d1-8a47-e611-84a6-00155d24b70c');


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

                        // console.log(data.cobalt_meetingId);
                        // console.log(cost);

                        data.cobalt_price = cost[0].Price;

                    } else {
                        data.cobalt_price = '0.0000';
                    }

                    // console.log(data.cobalt_price);

                    // console.log(`-------`);

                    data.cobalt_price = data.cobalt_price.slice(0, -2);

                    if(data.cobalt_OutsideProvider === 'true'){
                        data.cobalt_price = ' ';
                    }

                    const tags = data.cobalt_cobalt_tag_cobalt_meeting.map(function (data) {

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

                    if(data.cobalt_OutsideProvider === 'true'){
                        data.cobalt_Description = `${data.cobalt_Description}<br><input style="background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;" type="button" value="Register Now" onclick="window.location.href='${data.cobalt_OutsideProviderLink}'" />`
                    }else{
                        data.cobalt_Description = `${data.cobalt_Description}<br><input style="background-color: #4CAF50;border: none;color: white;padding: 15px 32px;text-align: center;text-decoration: none;display: inline-block;font-size: 16px;" type="button" value="Register Now" onclick="window.location.href='https://miamiportal.ramcoams.net/Authentication/DefaultSingleSignon.aspx?ReturnUrl=%2FEducation%2FRegistration%2FDetails.aspx%3Fcid%3D${data.cobalt_meetingId}'" />`
                    }

                    

                    data.cobalt_name = data.cobalt_name;

                    data.cobalt_cobalt_tag_cobalt_meeting = tags;

                    //console.debug(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${JSON.stringify(data)} \n`);

                    return data;
                });
            } else {

                modifiedData = [];

            }

            //sendSlackMessage(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] Formatted ${modifiedData.length} classes. Checking if classes exist in WordPress  \n`);
            resolve(modifiedData);

        })
            .catch(function (err) {
                reject(`Error: ${err}`);
            });
    });


    var data = await pullClasses;


    console.log(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] Formatted ${data.length} classes. Checking if classes exist in WordPress  \n`);
    fs.appendFile('logs/newClasses.log', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] Formatted ${data.length} classes. Checking if classes exist in WordPress  \n`, (err) => {
        if (err) throw err;
    });

    var existingClasses = [];
    var newClasses = [];

    for (i = 0; i < data.length; i++) {

        var checkIfExists = new Promise(function (resolve, reject) {

            setTimeout(function () {
                fetch(`${process.env.WORDPRESS_URL}/by-slug/${data[i].cobalt_meetingId}`)
                    .then(res => resolve(res.status))
                    .catch(err => reject(`Error: ${err}`));
            }, 1000)

        });

        try {
            var response = await checkIfExists;
        } catch (error) {
            console.log(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${error} \n`);
        };

        //console.log(data[i].cobalt_name);
        //console.log(response);
        //console.log(data[i].publish);

        console.log(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] Checking if "${data[i].cobalt_name} is already in WordPress." Hide_from_listing: ${data[i].publish} Response: ${response} \n`);
        fs.appendFile('logs/newClasses.log', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] Checking if "${data[i].cobalt_name} is already in WordPress." Hide_from_listing: ${data[i].publish} Response: ${response} \n`, (err) => {
            if (err) throw err;
        });

        if (response === 200 || response === 403) {
            existingClasses.push(data[i]);
        } else {
            newClasses.push(data[i]);
        }

    };



    //console.log(existingClasses.length);
    //console.log(newClasses.length);

    fs.appendFile('logs/newClasses.log', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${newClasses.length} new classes and ${existingClasses.length} existing classes found  \n`, (err) => {
        if (err) throw err;
    });

    console.log(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${newClasses.length} new classes and ${existingClasses.length} existing classes found  \n`);

    //sendSlackMessage(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${newClasses.length} new classes and ${existingClasses.length} existing classes found  \n`);


    submitNewClass(newClasses);

    function submitNewClass(data) {
        for (var i = 0; i < data.length; i++) {
            // for each iteration console.log a word
            // and make a pause after it
            (function (i) {
                setTimeout(function () {
                    var ramcoClass = {
                        "title": data[i].cobalt_name,
                        "status": "publish",
                        "hide_from_listings": data[i].publish,
                        "description": data[i].cobalt_Description,
                        "all_day": data[i].all_day,
                        "start_date": data[i].cobalt_BeginDate.Display,
                        "end_date": data[i].cobalt_EndDate.Display,
                        "slug": data[i].cobalt_meetingId,
                        "categories": data[i].cobalt_cobalt_tag_cobalt_meeting,
                        "show_map_link": true,
                        "show_map": true,
                        "cost": data[i].cobalt_price,
                        "tags": data[i].cobalt_cobalt_tag_cobalt_meeting
                        // "venue": {
                        //     "id": data[i].cobalt_Location
                        // }
                    };

                    fetch(process.env.WORDPRESS_URL, {
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

                                fs.appendFile('logs/results.json', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${data[i].cobalt_name} failed because of "${body.message}" \n`, (err) => {
                                    if (err) throw err;
                                });

                            } else {

                                //sendSlackMessage(`[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${data[i].cobalt_name} submitted successfully \n`);

                                fs.appendFile('logs/results.json', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] ${data[i].cobalt_name} submitted successfully \n`, (err) => {
                                    if (err) throw err;
                                });

                            }
                        });
                    console.log(`Class ${i + 1} out of ${data.length} new processed: ${data[i].cobalt_name}
                    `);
                    fs.appendFile('logs/newClasses.log', `[${moment().format('MM-DD-YYYY h:mm:ss a')}] Class ${i + 1} out of ${data.length} new processed: ${data[i].cobalt_name} \n`, (err) => {
                        if (err) throw err;
                    });
                }, 3000 * i);
            })(i);
        };

    }

}
